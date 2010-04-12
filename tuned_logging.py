# Copyright (C) 2008, 2009 Red Hat, Inc.
# Authors: Jan Vcelak <jvcelak@redhat.com>
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

import os, os.path
import logging
import logging.handlers

# configuration

LOG_FILENAME="/var/log/tuned/tuned.log"
LOG_FILE_MAXBYTES=100*1000
LOG_FILE_COUNT=2

# supportive functions

def disableString(name):
	level = logging._levelNames.get(str(name).upper(), logging.CRITICAL)
	logging.disable(level)

# customized logger

class TunedLogger (logging.getLoggerClass()):

	def setLevelString(self, name):
		self.level = logging._levelNames.get(str(name).upper(), logging.NOTSET)

	def switchToConsole(self):
		self._setupConsole()

		self.addHandler(self._console_handler)
		self.removeHandler(self._file_handler)

	def switchToFile(self):
		self._setupFile()

		self.addHandler(self._file_handler)
		self.removeHandler(self._console_handler)

	@classmethod
	def _setupConsole(cls):
		if cls._console_handler == None:
			cls._console_handler = logging.StreamHandler()
			cls._console_handler.setFormatter(cls._formatter)

	@classmethod
	def _setupFile(cls):
		if cls._file_handler == None:
			log_directory = os.path.dirname(LOG_FILENAME)
			if not os.path.exists(log_directory):
				os.makedirs(log_directory)

			cls._file_handler = logging.handlers.RotatingFileHandler(LOG_FILENAME,
					maxBytes=LOG_FILE_MAXBYTES, backupCount=LOG_FILE_COUNT)
			cls._file_handler.setFormatter(cls._formatter)

TunedLogger._formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
TunedLogger._console_handler = None;
TunedLogger._file_handler = None;

# initialization

logging.setLoggerClass(TunedLogger)
tuned_logger = logging.getLogger("tuned")
tuned_logger.setLevel(logging.INFO)

tuned_logger.switchToConsole()

