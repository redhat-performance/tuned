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

import daemon
import exports
import exports.dbus
import logs
import threading

log = logs.get()

DBUS_BUS = "com.redhat.tuned"
DBUS_INTERFACE = "com.redhat.tuned.control"
DBUS_OBJECT = "/Tuned"

dbus_exporter = exports.dbus.DBusExporter(DBUS_BUS, DBUS_INTERFACE, DBUS_OBJECT)
exports.register_exporter(dbus_exporter)

class Controller(exports.interfaces.ExportableInterface):
	"""
	Controller's purpose is to keep the program running, start/stop the tuning,
	and export the controller interface (currently only over D-Bus).
	"""

	def __init__(self, config_file, debug):
		super(self.__class__, self).__init__()
		exports.register_object(self)
		self._daemon = daemon.Daemon()
		self._terminate = threading.Event()
		if config_file:
			self.config_file = config_file

	def run(self):
		"""
		Controller main loop. The call is blocking.
		"""
		log.info("starting controller")
		exports.start()
		self.start()

		self._terminate.clear()
		# we have to pass some timeout, otherwise signals will not work
		while not self._terminate.wait(3600):
			pass

		log.info("terminating controller")
		exports.stop()
		self.stop()

	def terminate(self):
		self._terminate.set()

	@property
	def config_file(self):
		return self._config_file

	@config_file.setter
	def config_file(self, value):
		self._daemon.config_file = value
		self._config_file = value

	@exports.export("", "b")
	def start(self):
		if self._daemon.is_running():
			return True
		elif not self._daemon.is_enabled():
			return False
		else:
			return self._daemon.start()

	@exports.export("", "b")
	def stop(self):
		if not self._daemon.is_running():
			return True
		else:
			return self._daemon.stop()

	@exports.export("", "b")
	def reload(self):
		if not self._daemon.is_running():
			return False
		else:
			return self.stop() and self.start()

	@exports.export("s", "b")
	def switch_profile(self, profile):
		cfg = "/etc/tune-profiles/%s/tuned.conf" % (profile)
		try:
			self.config_file = cfg
		except ValueError as e:
			log.error("Unable to open profile's config file %s" % (cfg) )
			return False

		return self.reload()

	@exports.export("", "s")
	def active_profile(self):
		return self.config_file.split("/")[-2]

	@exports.export("", "a{bb}")
	def status(self):
		# TODO: add ktune status
		return [ self._daemon.is_running(), False ]
