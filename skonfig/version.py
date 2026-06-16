# -*- coding: utf-8 -*-
#
# 2022,2026 Dennis Camera (dennis.camera at riiengineering.ch)
# 2022-2023 Ander Punnar (ander at kvlt.ee)
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

def __silent_check_output(cmd, cwd):
    import os
    import subprocess
    try:
        # NOTE: subprocess.DEVNULL was added with Python 3.3
        devnull = os.open(os.devnull, os.O_RDONLY)
        return subprocess.check_output(
            cmd, cwd=cwd, stderr=devnull,
            shell=False).decode().rstrip()
    except InterruptedError:
        # retry
        return subprocess.run(cmd)
    finally:
        os.close(devnull)


def __silent_check_status(cmd, cwd):
    import os
    import subprocess

    try:
        # NOTE: subprocess.DEVNULL was added with Python 3.3
        devnull = os.open(os.devnull, os.O_RDONLY)
        return subprocess.run(
            cmd, cwd=cwd, stdin=devnull, stdout=devnull, stderr=devnull,
            shell=False, check=False).returncode
    finally:
        os.close(devnull)


def __guess_git_version():
    import os

    project_dir = os.path.dirname(os.path.dirname(__file__))

    # If .git exists (could be a directory or a file in case of a submodule) it
    # could be a Git repo, so try to generate version number from Git metadata.
    if os.path.exists(os.path.join(project_dir, ".git")):
        # Try to use Git to generate the version
        try:
            tag = __silent_check_output(
                ["git", "tag", "--points-at", "HEAD"],
                project_dir)

            if tag:
                version = tag
            else:
                commit_date = __silent_check_output(
                    ["git", "show", "-s", "--pretty=format:%cs", "HEAD"],
                    project_dir)
                version = "%s.dev%u" % (commit_date.replace("-", ""), 0)

            if 0 != __silent_check_status(
                    ["git", "diff-index", "--quiet", "HEAD", "--"],
                    project_dir):
                version += "+dirty"

            return version
        except Exception:
            pass

    return "0+unknown"


VERSION = __guess_git_version()
