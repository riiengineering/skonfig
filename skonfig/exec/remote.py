# -*- coding: utf-8 -*-
#
# 2011-2017 Steven Armstrong (steven-cdist at armstrong.cc)
# 2011-2013 Nico Schottelius (nico-cdist at schottelius.org)
# 2022,2023,2025 Dennis Camera (dennis.camera at riiengineering.ch)
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

import glob
import io
import os
import stat
import subprocess

import skonfig
import skonfig.logging

from contextlib import contextmanager

from skonfig.exec import util
from skonfig.util import (ipaddr, shquot)


def _wrap_addr(addr):
    """If addr is IPv6 then return addr wrapped between '[' and ']',
    otherwise return it unchanged."""
    if ipaddr.is_ipv6(addr):
        return "[%s]" % (addr)
    else:
        return addr


class DecodeError(skonfig.Error):
    def __init__(self, command):
        self.command = command

    def __str__(self):
        return "Cannot decode output of " + " ".join(self.command)


class Remote:
    """Execute commands remotely.

    All interaction with the target should be done through this class.
    Directly accessing the target from Python code is a bug!
    """
    def __init__(self,
                 target_host,
                 remote_exec,
                 base_path,
                 settings,
                 stdout_base_path=None,
                 stderr_base_path=None):
        self.target_host = target_host
        self._exec = shquot.split(remote_exec)

        self.archiving_mode = settings.archiving_mode
        self.base_path = base_path
        self.settings = settings

        self.stdout_base_path = stdout_base_path
        self.stderr_base_path = stderr_base_path

        self.conf_path = os.path.join(self.base_path, "conf")
        self.object_path = os.path.join(self.base_path, "object")

        self.type_path = os.path.join(self.conf_path, "type")
        self.global_explorer_path = os.path.join(self.conf_path, "explorer")

        self._open_logger()

        self._init_env()

    def _open_logger(self):
        self.log = skonfig.logging.getLogger(self.target_host[0])

    # logger is not pickable, so remove it when we pickle
    def __getstate__(self):
        state = self.__dict__.copy()
        if 'log' in state:
            del state['log']
        return state

    # recreate logger when we unpickle
    def __setstate__(self, state):
        self.__dict__.update(state)
        self._open_logger()

    def _init_env(self):
        """Setup environment for scripts."""
        # FIXME: better do so in exec functions that require it!
        os.environ['__remote_exec'] = shquot.join(self._exec)

    def create_files_dirs(self):
        self.rmdir(self.base_path)
        self.mkdir(self.base_path, umask=0o077)
        self.mkdir(self.conf_path)

    def remove_files_dirs(self):
        self.rmdir(self.base_path)

    def rmfile(self, path):
        """Remove file on the target."""
        self.log.trace("Remote rm: %s", path)
        self.run(["rm", "-f",  path])

    def rmdir(self, path):
        """Remove directory on the target."""
        self.log.trace("Remote rmdir: %s", path)
        self.run(["rm", "-r", "-f",  path])

    def mkdir(self, path, umask=None):
        """Create directory on the target."""
        self.log.trace("Remote mkdir: %s", path)

        cmd = "mkdir -p %s" % (shquot.quote(path))
        if umask is not None:
            mode = (0o777 & ~umask)
            cmd = "umask %04o; %s && chmod %o %s" % (
                umask, cmd, mode, shquot.quote(path))

        self.run(cmd)

    def tar_pipe_receiver(self, destination, tarmode):
        """Start a Tar extract command on the remote and read data from the
        process' standard input.
        """
        self.log.trace("Remote extract archive to: %s", destination)

        opts = "x"
        if tarmode is not None:
            opts += tarmode.extract_opts
        remote_command = "cd %s && tar %s" % (shquot.quote(destination), opts)

        return self._start_process(remote_command, stdin=subprocess.PIPE)

    def transfer(self, source, destination, umask=None):
        """Transfer a file or directory to the target."""
        self.log.trace("Remote transfer: %s -> %s", source, destination)

        if os.path.isdir(source):
            self._transfer_dir(source, destination, umask=umask)
        else:
            self._transfer_file(source, destination, umask=umask)

    def _transfer_file(self, source, destination, umask=None):
        remote_cmd = "cat >%s" % (shquot.quote(destination))
        if umask is not None:
            mode = (stat.S_IMODE(os.stat(source).st_mode) & ~umask)
            remote_cmd = "umask %04o; %s && chmod %o %s" % (
                umask, remote_cmd, mode, shquot.quote(destination))

        with open(source, "r") as f:
            self.run(remote_cmd, stdin=f)

    def _transfer_dir(self, source, destination, umask=None):
        archiving_mode = self.settings.archiving_mode

        if archiving_mode is None:
            # transfer directory one by one
            return self._transfer_dir_onebyone(
                source, destination, umask=umask)

        self.log.trace("Remote transfer in archiving mode")
        import skonfig.autil as autil

        try:
            # create destination directory on remote
            self.mkdir(destination, umask=umask)

            with self.tar_pipe_receiver(destination, archiving_mode) as tar_rx:
                autil.tar(source, dest=tar_rx.stdin, mode=archiving_mode)
        except autil.ArchivingNotEnoughFilesError as e:
            # archiving failed:
            # fall back to transfer directory one by one
            self.log.trace("Archiving failed: %s", e)
            return self._transfer_dir_onebyone(
                source, destination, umask=umask)

    def _transfer_dir_onebyone(self, source, destination, umask=None):
        # XXX: hmm, what if already created then tar pipe failed?
        self.mkdir(destination, umask=umask)

        # implement file filter just like for tar

        for path in glob.glob1(source, "*"):
            src_path = os.path.join(source, path)
            dst_path = os.path.join(destination, path)
            if os.path.isdir(src_path):
                self._transfer_dir_onebyone(src_path, dst_path, umask=umask)
            else:
                self._transfer_file(src_path, dst_path, umask=umask)

    def run_script(self, script, env=None, return_output=False, stdout=None,
                   stderr=None):
        """Run the given script with the given environment on the target.
        Return the output as a string.
        """

        command = ["exec", self.settings.remote_shell, "-e", script]

        return self.run(command, env=env, return_output=return_output,
                        stdout=stdout, stderr=stderr)

    def run(self, command, env=None, return_output=False,
            stdin=None, stdout=None, stderr=None):
        """Run the given command with the given environment on the target.
        Return the output as a string.

        If command is a list, each item of the list will be quoted if needed.
        If you need some part not to be quoted (e.g. the component is a glob),
        pass command as a str instead.
        """

        # environment variables can't be passed to the target,
        # so prepend command with variable declarations

        # The command with prepended variable assignments expects a
        # POSIX shell (bourne, bash) at the remote as user default shell.
        # If remote user shell isn't POSIX shell, but for e.g. csh/tcsh
        # then these var assignments are not var assignments for this
        # remote shell, it tries to execute it as a command and fails.
        # So really do this by default:
        # /bin/sh -c 'export <var assignments>; command'
        # so that constructed remote command isn't dependent on remote
        # shell. Do this only if env is not None. env breaks this.
        # Explicitly use /bin/sh, because var assignments assume POSIX
        # shell already.
        # This leaves the possibility to write script that needs to be run
        # remotely in e.g. csh and setting up SKONFIG_REMOTE_SHELL to e.g.
        # /bin/csh will execute this script in the right way.
        if env:
            if isinstance(command, (list, tuple)):
                command = shquot.join(command)

            remote_env = "export %s; " % (" ".join(
                "%s=%s" % (
                    name, shquot.quote(value) if value else "")
                for (name, value) in env.items()))
            command = ["/bin/sh", "-c", remote_env + command]

        return self._run_command(command, env=env, return_output=return_output,
                                 stdin=stdin, stdout=stdout, stderr=stderr)

    def _run_command(self, argv, env=None, return_output=False,
                     stdin=None, stdout=None, stderr=None):
        if return_output:
            if stdout is not None:
                raise skonfig.Error(
                    "cannot use return_output and stdout together")
            stdout = subprocess.PIPE

        with self._start_process(
                argv=argv, extra_env=env,
                stdin=stdin, stdout=stdout, stderr=stderr) as proc:
            try:
                if return_output:
                    stdout = io.BytesIO()
                    stdout.write(proc.stdout.read())
                exit_status = proc.wait()
            except:
                proc.kill()
                # don’t call proc.wait() again as proc.__exit__ does it
                raise

        if exit_status:
            raise skonfig.Error(shquot.join(argv))
        if return_output:
            return stdout.getvalue().decode()

    @contextmanager
    def _start_process(self, argv, extra_env={}, stdin=None, stdout=None, stderr=None):
        if isinstance(argv, (list, tuple)):
            remote_cmd_string = shquot.join(argv)
        else:
            remote_cmd_string = argv

        close_afterwards = []
        if stdout is None:
            stdout = util.get_std_fd(self.stdout_base_path, "remote")
            close_afterwards.append(stdout)
        if stderr is None:
            stderr = util.get_std_fd(self.stderr_base_path, "remote")
            close_afterwards.append(stderr)

        # prepare environment
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        # export __target_host, __target_hostname, __target_fqdn
        # for use in __remote_exec scripts
        env.update(zip(
            ("__target_host", "__target_hostname", "__target_fqdn"),
            self.target_host))

        try:
            self.log.trace("Remote run: %s", remote_cmd_string)

            proc = subprocess.Popen(
                (self._exec + [self.target_host[0], remote_cmd_string]),
                env=env, shell=False,
                stdin=stdin, stdout=stdout, stderr=stderr)
            yield proc

            if proc.stdout and proc.stdout.seekable():
                util.log_std_fd(self.log, argv, proc.stdout, "Remote stdout")
            if proc.stderr and proc.stderr.seekable():
                util.log_std_fd(self.log, argv, proc.stderr, "Remote stderr")
        except UnicodeDecodeError:
            raise DecodeError(argv)
        finally:
            for fd in close_afterwards:
                if isinstance(fd, int):
                    os.close(fd)
                else:
                    fd.close()
