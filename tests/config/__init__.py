# -*- coding: utf-8 -*-
#
# 2010-2017 Steven Armstrong (steven-cdist at armstrong.cc)
# 2012-2015 Nico Schottelius (nico-cdist at schottelius.org)
# 2014 Daniel Heule (hda at sfs.biz)
#
# This file is part of skonfig.
#
# skonfig is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# skonfig is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with skonfig. If not, see <http://www.gnu.org/licenses/>.
#

import os
import shutil

import skonfig
import skonfig.config
import skonfig.core.cdist_type
import skonfig.core.cdist_object
import skonfig.util
import skonfig.settings

import tests as test

from skonfig import core

my_dir = os.path.abspath(os.path.dirname(__file__))
fixtures = os.path.join(my_dir, 'fixtures')
conf_dir = os.path.join(fixtures, 'conf')
type_base_path = os.path.join(conf_dir, 'type')

expected_object_names = list(sorted((
    "__first/man",
    "__second/on-the",
    "__third/moon")))


class CdistObjectErrorContext:
    def __init__(self, original_error):
        self.original_error = original_error

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            if exc_value.original_error:
                raise exc_value.original_error


@test.patch.dict("os.environ")
class ConfigRunTestCase(test.SkonfigTestCase):

    def setUp(self):
        self.temp_dir = self.mkdtemp()

        self.settings = skonfig.settings.SettingsContainer()
        self.settings.conf_dir = [conf_dir]

        self.local_dir = os.path.join(self.temp_dir, "local")
        self.hostdir = skonfig.util.str_hash(self.target_host[0])
        self.host_base_path = os.path.join(self.local_dir, self.hostdir)
        os.makedirs(self.host_base_path)

        self.local = skonfig.exec.local.Local(
            self.target_host,
            self.host_base_path,
            self.settings)

        # Setup test objects
        self.object_base_path = os.path.join(self.temp_dir, 'object')

        self.objects = []
        for cdist_object_name in expected_object_names:
            (cdist_type, cdist_object_id) = cdist_object_name.split("/", 1)
            cdist_object = core.CdistObject(
                core.CdistType(type_base_path, cdist_type),
                self.object_base_path,
                self.local.object_marker_name,
                cdist_object_id)
            cdist_object.create()
            self.objects.append(cdist_object)

        self.object_index = dict((o.name, o) for o in self.objects)
        self.object_names = [o.name for o in self.objects]

        self.remote_dir = os.path.join(self.temp_dir, "remote")
        os.mkdir(self.remote_dir)
        self.remote = skonfig.exec.remote.Remote(
            self.target_host,
            self.remote_exec,
            self.remote_dir,
            self.settings,
            stdout_base_path=self.local.stdout_base_path,
            stderr_base_path=self.local.stderr_base_path)

        self.local.object_path = self.object_base_path
        self.local.type_path = type_base_path

        self.config = skonfig.config.Config(self.local, self.remote)

    def tearDown(self):
        for o in self.objects:
            o.requirements = []
            o.state = ""

        shutil.rmtree(self.temp_dir)

    def assertRaisesObjectError(self, original_error, callable_obj):
        """Test if a raised skonfig.ObjectError was caused by the given
        original_error.
        """
        with self.assertRaises(original_error):
            try:
                callable_obj()
            except skonfig.ObjectError as e:
                if e.original_error:
                    raise e.original_error
                else:
                    raise

    def test_dependency_resolution(self):
        first = self.object_index['__first/man']
        second = self.object_index['__second/on-the']
        third = self.object_index['__third/moon']

        first.requirements = [second.name]
        second.requirements = [third.name]

        # First run:
        # solves first and maybe second (depending on the order in the set)
        self.config.iterate_once()
        self.assertTrue(third.state == third.STATE_DONE)

        self.config.iterate_once()
        self.assertTrue(second.state == second.STATE_DONE)

        try:
            self.config.iterate_once()
        except skonfig.Error:
            # Allow failing, because the third run may or may not be
            # unecessary already,
            # depending on the order of the objects
            pass
        self.assertTrue(first.state == first.STATE_DONE)

    def test_unresolvable_requirements(self):
        """Ensure an exception is thrown for unresolvable depedencies"""

        # Create to objects depending on each other - no solution possible
        first = self.object_index['__first/man']
        second = self.object_index['__second/on-the']

        first.requirements = [second.name]
        second.requirements = [first.name]

        self.assertRaisesObjectError(
            skonfig.UnresolvableRequirementsError,
            self.config.iterate_until_finished)

    def test_missing_requirements(self):
        """Throw an error if requiring something non-existing"""
        first = self.object_index['__first/man']
        first.requirements = ['__first/not/exist']
        self.assertRaisesObjectError(
            skonfig.UnresolvableRequirementsError,
            self.config.iterate_until_finished)

    def test_requirement_broken_type(self):
        """Unknown type should be detected in the resolving process"""
        first = self.object_index['__first/man']
        first.requirements = ['__nosuchtype/not/exist']
        self.assertRaisesObjectError(
            skonfig.core.cdist_type.InvalidTypeError,
            self.config.iterate_until_finished)

    def test_requirement_singleton_where_no_singleton(self):
        """Missing object id should be detected in the resolving process"""
        first = self.object_index['__first/man']
        first.requirements = ['__first']
        self.assertRaisesObjectError(
            skonfig.core.cdist_object.MissingObjectIdError,
            self.config.iterate_until_finished)

    def test_dryrun(self):
        """Test if the dryrun option is working like expected"""
        dry_local = skonfig.exec.local.Local(
            self.target_host,
            self.host_base_path,
            self.settings,
            initial_manifest=os.path.join(
                fixtures, "manifest", "dryrun_manifest"),
            # exec_path can not derived from sys.argv in unittests
            exec_path=test.skonfig_exec_path)

        dryrun_config = skonfig.config.Config(
            dry_local, self.remote, dry_run=True)
        dryrun_config.run()
        # if we are here, dry runs work like expected

    def test_deps_resolver(self):
        """Test to show dependency resolver warning message."""
        local = skonfig.exec.local.Local(
            self.target_host,
            self.host_base_path,
            self.settings,
            initial_manifest=os.path.join(
                fixtures, "manifest", "init-deps-resolver"),
            exec_path=test.skonfig_exec_path)

        # dry_run is ok for dependency testing
        config = skonfig.config.Config(local, self.remote, dry_run=True)
        config.run()

    def test_graph_check_cycle_empty(self):
        graph = {}
        (has_cycle, path) = skonfig.config.graph_check_cycle(graph)
        self.assertFalse(has_cycle)

    def test_graph_check_cycle_1(self):
        #
        # a -> b -> c
        #      |
        #      +--> d -> e
        graph = {
            'a': ['b'],
            'b': ['c', 'd'],
            'd': ['e'],
            }
        (has_cycle, path) = skonfig.config.graph_check_cycle(graph)
        self.assertFalse(has_cycle)

    def test_graph_check_cycle_2(self):
        #
        # a -> b -> c
        # /\        |
        #  \        |
        #   +-------+
        graph = {
            'a': ['b'],
            'b': ['c'],
            'c': ['a'],
            }
        (has_cycle, path) = skonfig.config.graph_check_cycle(graph)
        self.assertTrue(has_cycle)
        self.assertGreater(path.count(path[-1]), 1)

    def test_graph_check_cycle_3(self):
        #
        # a -> b -> c
        #  \        \
        #   \        +--> g
        #    \            /\
        #     \           /|
        #      +-> d -> e  |
        #           \      |
        #            + --> f
        #
        # h -> i --> j
        # |    /\    |
        # \/    |    \/
        # n     m <- k
        graph = {
            'a': ['b', 'd'],
            'b': ['c'],
            'c': ['g'],
            'd': ['e', 'f'],
            'e': ['g'],
            'f': ['g'],
            'h': ['i', 'n'],
            'i': ['j'],
            'j': ['k'],
            'k': ['m'],
            'm': ['i'],
            }
        (has_cycle, path) = skonfig.config.graph_check_cycle(graph)
        self.assertTrue(has_cycle)
        self.assertGreater(path.count(path[-1]), 1)


# Currently the resolving code will simply detect that this object does
# not exist. It should probably check if the type is a singleton as well
# - but maybe only in the emulator - to be discussed.
#
#    def test_requirement_no_singleton_where_singleton(self):
#        """Missing object id should be detected in the resolving process"""
#        first = self.object_index['__first/man']
#        first.requirements = ['__singleton_test/foo']
#        with self.assertRaises(skonfig.core.?????):
#            self.config.iterate_until_finished()

if __name__ == "__main__":
    import unittest

    unittest.main()
