# -*- coding: utf-8 -*-
#
# 2011-2017 Steven Armstrong (steven-cdist at armstrong.cc)
# 2012-2015 Nico Schottelius (nico-cdist at schottelius.org)
#
# This file is part of cdist.
#
# cdist is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cdist is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with cdist. If not, see <http://www.gnu.org/licenses/>.
#
#

import getpass
import os
import shutil
import logging

import cdist
import cdist.util
import skonfig.settings

from cdist import (core, test)
from cdist.core import code
from cdist.exec import (local, remote)

my_dir = os.path.abspath(os.path.dirname(__file__))
fixtures = os.path.join(my_dir, 'fixtures')
conf_dir = os.path.join(fixtures, 'conf')


class CodeTestCase(test.CdistTestCase):

    def setUp(self):
        self.local_dir = self.mkdtemp()
        self.hostdir = cdist.util.str_hash(self.target_host[0])
        self.host_base_path = os.path.join(self.local_dir, self.hostdir)

        self.settings = skonfig.settings.SettingsContainer()
        self.settings.conf_dir = [conf_dir]
        self.settings.remote_exec = self.remote_exec

        self.local = local.Local(
            self.target_host,
            self.host_base_path,
            self.settings,
            exec_path=cdist.test.cdist_exec_path)

        self.local.create_files_dirs()

        self.remote_dir = self.mkdtemp()
        self.remote = remote.Remote(
            self.target_host,
            remote_exec=self.settings.remote_exec,
            base_path=self.remote_dir,
            settings=self.settings,
            stdout_base_path=self.local.stdout_base_path,
            stderr_base_path=self.local.stderr_base_path)
        self.remote.create_files_dirs()

        self.code = code.Code(self.target_host, self.local, self.remote)

        self.cdist_type = core.CdistType(self.local.type_path,
                                         '__dump_environment')
        self.cdist_object = core.CdistObject(
                self.cdist_type, self.local.object_path, 'whatever',
                self.local.object_marker_name)
        self.cdist_object.create()

    def tearDown(self):
        shutil.rmtree(self.local_dir)
        shutil.rmtree(self.remote_dir)

    def test_run_gencode_local_environment(self):
        output_string = self.code.run_gencode_local(self.cdist_object)
        output_dict = {}
        for line in output_string.split('\n'):
            if line:
                (junk, value) = line.split(': ')
                key = junk.split(' ')[1]
                output_dict[key] = value
        self.assertEqual(output_dict['__target_host'],
                         self.local.target_host[0])
        self.assertEqual(output_dict['__target_hostname'],
                         self.local.target_host[1])
        self.assertEqual(output_dict['__target_fqdn'],
                         self.local.target_host[2])
        self.assertEqual(output_dict['__global'], self.local.base_path)
        self.assertEqual(output_dict['__type'], self.cdist_type.absolute_path)
        self.assertEqual(output_dict['__object'],
                         self.cdist_object.absolute_path)
        self.assertEqual(output_dict['__object_id'],
                         self.cdist_object.object_id)
        self.assertEqual(output_dict['__object_name'], self.cdist_object.name)
        self.assertEqual(output_dict['__files'], self.local.files_path)
        self.assertEqual(output_dict['__target_host_tags'], '')
        self.assertEqual(output_dict['__cdist_log_level'],
                         str(logging.WARNING))
        self.assertEqual(output_dict['__cdist_log_level_name'], 'WARNING')

    def test_run_gencode_remote_environment(self):
        output_string = self.code.run_gencode_remote(self.cdist_object)
        output_dict = {}
        for line in output_string.split('\n'):
            if line:
                (junk, value) = line.split(': ')
                key = junk.split(' ')[1]
                output_dict[key] = value
        self.assertEqual(output_dict['__target_host'],
                         self.local.target_host[0])
        self.assertEqual(output_dict['__target_hostname'],
                         self.local.target_host[1])
        self.assertEqual(output_dict['__target_fqdn'],
                         self.local.target_host[2])
        self.assertEqual(output_dict['__global'], self.local.base_path)
        self.assertEqual(output_dict['__type'], self.cdist_type.absolute_path)
        self.assertEqual(output_dict['__object'],
                         self.cdist_object.absolute_path)
        self.assertEqual(output_dict['__object_id'],
                         self.cdist_object.object_id)
        self.assertEqual(output_dict['__object_name'], self.cdist_object.name)
        self.assertEqual(output_dict['__files'], self.local.files_path)
        self.assertEqual(output_dict['__target_host_tags'], '')
        self.assertEqual(output_dict['__cdist_log_level'],
                         str(logging.WARNING))
        self.assertEqual(output_dict['__cdist_log_level_name'], 'WARNING')

    def test_transfer_code_remote(self):
        self.cdist_object.code_remote = self.code.run_gencode_remote(
                self.cdist_object)
        self.code.transfer_code_remote(self.cdist_object)
        destination = os.path.join(self.remote.object_path,
                                   self.cdist_object.code_remote_path)
        self.assertTrue(os.path.isfile(destination))

    def test_run_code_local(self):
        self.cdist_object.code_local = self.code.run_gencode_local(
                self.cdist_object)
        self.code.run_code_local(self.cdist_object)

    def test_run_code_remote_environment(self):
        self.cdist_object.code_remote = self.code.run_gencode_remote(
                self.cdist_object)
        self.code.transfer_code_remote(self.cdist_object)
        self.code.run_code_remote(self.cdist_object)


if __name__ == '__main__':
    import unittest
    unittest.main()
