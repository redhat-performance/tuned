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

import logging
import logging.handlers

class TunedLogger (logging.getLoggerClass()):

	def setLevelString(self, name):
		name = str(name)
		if name.isdigit():
			level = int(name)
		else:
			level = logging._levelNames.get(name.upper(), logging.NOTSET)

		self.level = level

	def switchToConsole(self):
		self.addHandler(console_handler)
		self.removeHandler(file_handler)

	def switchToFile(self):
		self.addHandler(file_handler)
		self.removeHandler(console_handler)

logging.setLoggerClass(TunedLogger)

######

console_handler = logging.StreamHandler()
file_handler = logging.handlers.RotatingFileHandler("/tmp/tuned.log", maxBytes=200*1000, backupCount=2)

tuned_logger = logging.getLogger("tuned")
tuned_logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

tuned_logger.switchToConsole()

