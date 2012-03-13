# Copyright (C) 2008-2011 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#

import atexit
import logging
import logging.handlers
import os
import os.path
import inspect

__all__ = ["get"]

LOG_FILENAME = "/var/log/tuned/tuned.log"
LOG_FILE_MAXBYTES = 100*1000
LOG_FILE_COUNT = 2

root_logger = None

def get():
	global root_logger
	if root_logger is None:
		root_logger = logging.getLogger("tuned")

	calling_module = inspect.currentframe().f_back
	name = calling_module.f_locals["__name__"]
	if name == "__main__":
		name = "tuned"
		return root_logger
	elif name.startswith("tuned."):
		(root, child) = name.split(".", 1)
		child_logger = root_logger.getChild(child)
		child_logger.setLevel("NOTSET")
		return child_logger
	else:
		assert False

class TunedLogger(logging.getLoggerClass()):
	"""Custom tuned daemon logger class."""
	_formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
	_console_handler = None
	_file_handler = None

	def __init__(self, *args, **kwargs):
		super(self.__class__, self).__init__(*args, **kwargs)
		self.setLevel(logging.INFO)
		self.switch_to_console()
		self.propagate = False

	def set_level(self, level, default = logging.NOTSET):
		"""Set logging level. The 'level' parameter can be str or logging module constant."""
		if type(level) is str:
			level = logging._levelNames.get(level.upper(), logging.NOTSET)
		self.level = level

	def switch_to_console(self):
		self._setup_console_handler()
		self.addHandler(self._console_handler)
		self.removeHandler(self._file_handler)

	def switch_to_file(self):
		self._setup_file_handler()
		self.addHandler(self._file_handler)
		self.removeHandler(self._console_handler)

	@classmethod
	def _setup_console_handler(cls):
		if cls._console_handler is not None:
			return

		cls._console_handler = logging.StreamHandler()
		cls._console_handler.setFormatter(cls._formatter)

	@classmethod
	def _setup_file_handler(cls):
		if cls._file_handler is not None:
			return

		log_directory = os.path.dirname(LOG_FILENAME)
		if not os.path.exists(log_directory):
			os.makedirs(log_directory)

		cls._file_handler = logging.handlers.RotatingFileHandler(
			LOG_FILENAME, maxBytes=LOG_FILE_MAXBYTES, backupCount=LOG_FILE_COUNT)
		cls._file_handler.setFormatter(cls._formatter)

logging.setLoggerClass(TunedLogger)
atexit.register(logging.shutdown)
