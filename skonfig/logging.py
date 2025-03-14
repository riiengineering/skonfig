# -*- coding: utf-8 -*-
#
# 2025 Dennis Camera (dennis.camera at riiengineering.ch)
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

import collections
import logging as _logging


def setup_logging():
    _logging.setLoggerClass(SkonfigLog)

    # define additional logging levels

    _logging.OFF = (_logging.CRITICAL + 10)  # disable logging
    _logging.addLevelName(_logging.OFF, "OFF")

    _logging.VERBOSE = (_logging.INFO - 5)
    _logging.addLevelName(_logging.VERBOSE, "VERBOSE")

    _logging.TRACE = (_logging.DEBUG - 5)
    _logging.addLevelName(_logging.TRACE, "TRACE")


def log_level_env_var_val(log):
    return str(log.getEffectiveLevel())


def log_level_name_env_var_val(log):
    return _logging.getLevelName(log.getEffectiveLevel())


class ColourFormatter(_logging.Formatter):
    use_colours = False

    RESET = "\033[0m"
    COLOUR_MAP = {
        "CRITICAL": "\033[0;91m",  # bright red
        "ERROR": "\033[0;31m",     # red
        "WARNING": "\033[0;33m",   # yellow
        "INFO": "\033[0;94m",      # bright blue
        "VERBOSE": "\033[0;30m",   # black
        "DEBUG": "\033[0;90m",     # bright black (gray)
        "TRACE": "\033[0;37m",     # white
        }

    def format(self, record):
        msg = super().format(record)
        if self.use_colours:
            colour = self.COLOUR_MAP.get(record.levelname)
            if colour:
                 msg = (colour + msg + self.RESET)
        return msg


class SkonfigLog(_logging.Logger):
    FORMAT = "%(levelname)s: %(name)s: %(message)s"

    class StdoutFilter(_logging.Filter):
        def filter(self, rec):
            return rec.levelno < _logging.ERROR

    class StderrFilter(_logging.Filter):
        def filter(self, rec):
            return rec.levelno >= _logging.ERROR

    def __init__(self, name):
        import sys

        super().__init__(name)
        self.propagate = False

        formatter = ColourFormatter(self.FORMAT)

        stdout_handler = _logging.StreamHandler(sys.stdout)
        stdout_handler.addFilter(self.StdoutFilter())
        stdout_handler.setLevel(_logging.TRACE)
        stdout_handler.setFormatter(formatter)

        stderr_handler = _logging.StreamHandler(sys.stderr)
        stderr_handler.addFilter(self.StderrFilter())
        stderr_handler.setLevel(_logging.ERROR)
        stderr_handler.setFormatter(formatter)

        self.addHandler(stdout_handler)
        self.addHandler(stderr_handler)

    def verbose(self, msg, *args, **kwargs):
        self.log(_logging.VERBOSE, msg, *args, **kwargs)

    def trace(self, msg, *args, **kwargs):
        self.log(_logging.TRACE, msg, *args, **kwargs)
