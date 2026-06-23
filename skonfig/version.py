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
    from datetime import (datetime, timezone)

    project_dir = os.path.dirname(os.path.dirname(__file__))
    date_format = "%Y%m%d"

    version_date = datetime.today()
    dev_id = None
    version_suffix = ""

    # if .git exists (directory or a file in case of a submodule) it could be
    # a Git repo, so try to generate the version number from Git metadata.
    if os.path.exists(os.path.join(project_dir, ".git")):
        try:
            tag = __silent_check_output(
                ["git", "tag", "--points-at", "HEAD"],
                project_dir)

            try:
                version_date = datetime.strptime(tag, date_format)
            except ValueError:
                tag = None

            if not tag:
                commit_date = __silent_check_output(
                    ["git", "show", "-s", "--pretty=format:%cI", "HEAD"],
                    project_dir)
                version_date = datetime.strptime(commit_date, "%Y-%m-%dT%H:%M:%S%:z")
                dev_id = 0

            if 0 != __silent_check_status(
                    ["git", "diff-index", "--quiet", "HEAD", "--"],
                    project_dir):
                version_suffix += "+dirty"
        except Exception:
            pass
    # if .got exists it is a Got working directory, so try to generate the
    # version number from Git metadata.
    elif os.path.exists(os.path.join(project_dir, ".got")):
        try:
            with open(os.path.join(project_dir, ".got", "base-commit")) as f:
                base_commit = f.read().strip()

            import re
            tag_re = re.compile(r"^[0-9]{4}(?:-[0-9]{2}){2} commit:([0-9a-f]+) (.*?):")
            for line in __silent_check_output(["got", "tag", "-ls"], project_dir).splitlines():
                tag_match = tag_re.match(line)
                if tag_match is None:
                    continue
                if base_commit.startswith(tag_match[1]):
                    try:
                        version_date = datetime.strptime(tag_match[2], date_format)
                        break
                    except ValueError:
                        pass
            else:
                for line in __silent_check_output(
                        ["got", "log", "-c", base_commit, "-x", base_commit],
                        project_dir).splitlines():
                    if not line.strip():
                        break
                    try:
                        (k, v) = line.split(": ", 1)
                    except ValueError:
                        continue

                    if k == "date":
                        version_date = datetime.strptime(v, "%a %b %d %H:%M:%S %Y %Z")
                        dev_id = 0
                        break

            if __silent_check_output(["got", "status"], project_dir):
                version_suffix += "+dirty"
        except Exception:
            pass

    return "%s%s%s" % (
        version_date.astimezone(timezone.utc).strftime("%Y%m%d"),
        ".dev%u" % dev_id if dev_id is not None else "",
        version_suffix)



VERSION = __guess_git_version()
