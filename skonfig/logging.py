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

import logging as _logging

get_logger = _logging.getLogger
root = _logging.root


def set_log_level(loglevel):
    root.setLevel(loglevel)


def colours_enabled():
    return ColourFormatter.use_colours


def set_colours(flag):
    ColourFormatter.use_colours = flag


# logging levels

CRITICAL = _logging.CRITICAL
ERROR = _logging.ERROR
WARNING = _logging.WARNING
INFO = _logging.INFO
DEBUG = _logging.DEBUG

# skonfig extensions:
OFF = (_logging.CRITICAL + 10)  # disable logging
TRACE = (_logging.DEBUG - 5)
VERBOSE = (_logging.INFO - 5)

_logging.addLevelName(OFF, "OFF")
_logging.addLevelName(TRACE, "TRACE")
_logging.addLevelName(VERBOSE, "VERBOSE")

_logging.Logger.trace = lambda self, *args, **kwargs: \
    self.log(TRACE, *args, **kwargs)

_logging.Logger.verbose = lambda self, *args, **kwargs: \
    self.log(VERBOSE, *args, **kwargs)


def setup_logging():
    _logging.setLoggerClass(SkonfigLog)


def level_env_val(log):
    return str(log.getEffectiveLevel())


def level_name_env_val(log):
    return _logging.getLevelName(log.getEffectiveLevel())


def level_name_to_int(s):
    # < Python 3.4
    levels_pre34 = getattr(_logging, "_levelNames", {})
    # >= Python 3.4
    levels_available = getattr(_logging, "_levelToName", levels_pre34)

    for (level, level_name) in levels_available.items():
        if s == level_name:
            return level

    return None


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
        stdout_handler.setLevel((_logging.NOTSET + 1))
        stdout_handler.setFormatter(formatter)

        stderr_handler = _logging.StreamHandler(sys.stderr)
        stderr_handler.addFilter(self.StderrFilter())
        stderr_handler.setLevel(_logging.ERROR)
        stderr_handler.setFormatter(formatter)

        self.addHandler(stdout_handler)
        self.addHandler(stderr_handler)
