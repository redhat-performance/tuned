# Copyright (C) 2008-2012 Red Hat, Inc.
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

__all__ = ["Application"]

import controller
import daemon
import exports
import exports.dbus
import monitors
import plugins
import signal
import storage
import units
import utils

DBUS_BUS = "com.redhat.tuned"
DBUS_INTERFACE = "com.redhat.tuned.control"
DBUS_OBJECT = "/Tuned"

class Application(object):
	def __init__(self, config_file, enable_dbus = True):
		self._storage_provider = storage.PickleProvider()
		self._storage_factory = storage.Factory(self._storage_provider)

		self._plugins_repository = plugins.Repository(self._storage_provider)
		self._monitors_repository = monitors.Repository()
		self._unit_manager = units.Manager(self._plugins_repository, self._monitors_repository)

		self._daemon = daemon.Daemon(self._unit_manager)
		self._controller = controller.Controller(self._daemon, config_file)

		self._dbus_exporter = None
		if enable_dbus:
			self._init_dbus()

		self._init_signals()

	def _init_dbus(self):
		self._dbus_exporter = exports.dbus.DBusExporter(DBUS_BUS, DBUS_INTERFACE, DBUS_OBJECT)
		exports.register_exporter(self._dbus_exporter)
		exports.register_object(self._controller)

	def _init_signals(self):
		utils.handle_signal(signal.SIGHUP, self._controller.switch_to_default_profile)
		utils.handle_signal([signal.SIGINT, signal.SIGTERM], self._controller.terminate)

	@property
	def daemon(self):
		return self._daemon

	@property
	def controller(self):
		return self._controller

	def run(self):
		exports.start()
		result = self._controller.run()
		exports.stop()

		return result
