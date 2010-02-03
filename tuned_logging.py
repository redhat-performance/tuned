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

LOG_FILENAME="/var/log/tuned/tuned.log"

class TunedLogger (logging.getLoggerClass()):

	def setLevelString(self, name):
		self.level = logging._levelNames.get(str(name).upper(), logging.NOTSET)

	def switchToConsole(self):
		self.addHandler(console_handler)
		self.removeHandler(file_handler)

	def switchToFile(self):
		self.addHandler(file_handler)
		self.removeHandler(console_handler)

def disableString(name):
	level = logging._levelNames.get(str(name).upper(), logging.CRITICAL)
	logging.disable(level)

logging.setLoggerClass(TunedLogger)

# intialization

tuned_logger = logging.getLogger("tuned")
tuned_logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")

console_handler = logging.StreamHandler()

log_directory = os.path.dirname(LOG_FILENAME)
if not os.path.exists(log_directory):
	os.makedirs(log_directory)

file_handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=200*1000, backupCount=2)

console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

tuned_logger.switchToConsole()

