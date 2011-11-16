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

__all__ = ["Controller"]

import exports
import exports.dbus
import logs

log = logs.get("tuned")

DBUS_BUS = "com.redhat.tuned"
DBUS_INTERFACE = "com.redhat.tuned.control"
DBUS_OBJECT = "/Tuned"

dbus_exporter = exports.dbus.DBusExporter(DBUS_BUS, DBUS_INTERFACE, DBUS_OBJECT)
exports.register_exporter(dbus_exporter)

class Controller(exports.interfaces.IExportable):
	def __init__(self, config_file, debug):
		super(self.__class__, self).__init__()
		exports.register_object(self)
		self._daemon = None
		self._terminating = False

	def run(self):
		exports.start()
		i = 0
		import time
		while not self._terminating:
			i += 1
			log.critical("controller run loop %d" % i)
			time.sleep(1)
		exports.stop()

	def terminate(self):
		self._terminating = True

	@exports.export("", "b")
	def start(self):
		return False

	@exports.export("", "b")
	def stop(self):
		return False

	@exports.export("", "b")
	def reload(self):
		return False

	@exports.export("s", "b")
	def switch_profile(self, profile):
		return False

	@exports.export("", "s")
	def active_profile(self):
		return "default"

	@exports.export("", "a{bb}")
	def status(self):
		return [ False, False ]
