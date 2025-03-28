# -*- coding: utf-8 -*-
#
# 2017 Darko Poljak (darko.poljak at gmail.com)
# 2023 Dennis Camera (dennis.camera at riiengineering.ch)
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
import os
import re
import tarfile
import tempfile
import time


class ArchivingNotEnoughFilesError(RuntimeError):
    pass


class ArchivingMode:
    @classmethod
    def is_supported(cls):
        if cls.tarmode:
            return cls.tarmode in tarfile.TarFile.OPEN_METH
        else:
            # plain tar is always supported
            return True

    @classmethod
    def name(cls):
        return cls.__name__.lower()

    @classmethod
    def doc(cls):
        return cls.__doc__


class TAR(ArchivingMode):
    "tar archive"
    tarmode = ""
    file_ext = ".tar"
    extract_opts = ""


class TGZ(ArchivingMode):
    "gzip tar archive"
    tarmode = "gz"
    file_ext = ".tar.gz"
    extract_opts = "z"


class TBZ2(ArchivingMode):
    "bzip2 tar archive"
    tarmode = "bz2"
    file_ext = ".tar.bz2"
    extract_opts = "j"


class TXZ(ArchivingMode):
    "lzma tar archive"
    tarmode = "xz"
    file_ext = ".tar.xz"
    extract_opts = "J"


archiving_modes = [TAR, TGZ, TBZ2, TXZ]


def mode_from_str(s):
    if s is None:
        return None

    s_lc = s.lower()

    if s_lc == "none":
        # special case to disable the archiving feature
        return None

    for mode in archiving_modes:
        if (mode.name() == s_lc):
            break
    else:
        raise ValueError("invalid archiving mode: %s" % (s))

    # check if the method is supported by this python version
    if not mode.is_supported():
        raise RuntimeError(
            "the archiving mode '%s' is not supported by this version of "
            "Python" % (mode.name()))

    return mode


# Archiving will be enabled if directory contains >= FILES_LIMIT files.
FILES_LIMIT = 2


def tar(source, dest=None, mode=TGZ):
    fcnt = len(os.listdir(source)) if os.path.isdir(source) else 1
    if fcnt < FILES_LIMIT:
        raise ArchivingNotEnoughFilesError(
            "file count %u is lower than %d limit" % (fcnt, FILES_LIMIT))

    tarmode = "w|%s" % (mode.tarmode)

    (tarpath, tarfh) = (None, None)
    if isinstance(dest, str):
        tarpath = dest
    elif dest is not None:
        tarfh = dest
    else:
        # write to temporary file
        (tarfh, tarpath) = tempfile.mkstemp(suffix=mode.file_ext)

    time_now = time.time()

    def tar_filter(tarinfo):
        tarinfo.uid = 0
        tarinfo.uname = ""
        tarinfo.gid = 0
        tarinfo.gname = ""
        tarinfo.mtime = time_now
        return tarinfo

    with tarfile.open(
        tarpath,
        tarmode,
        fileobj=tarfh,
        dereference=True,
        format=tarfile.USTAR_FORMAT
    ) as tar:
        for f in sorted(os.listdir(source)):
            tar.add(os.path.join(source, f), arcname=f, recursive=True, filter=tar_filter)

    return (tarfh, tarpath)
