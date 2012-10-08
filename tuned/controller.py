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

__all__ = ["Controller"]

import exports
import logs
import threading

log = logs.get()

class Controller(exports.interfaces.ExportableInterface):
	"""
	Controller's purpose is to keep the program running, start/stop the tuning,
	and export the controller interface (currently only over D-Bus).
	"""

	def __init__(self, daemon):
		super(self.__class__, self).__init__()
		self._daemon = daemon
		self._terminate = threading.Event()

	def run(self):
		"""
		Controller main loop. The call is blocking.
		"""
		log.info("starting controller")
		self.start()

		self._terminate.clear()
		# we have to pass some timeout, otherwise signals will not work
		while not self._terminate.wait(3600):
			pass

		log.info("terminating controller")
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
	def switch_profile(self, profile_name):
		was_running = self._daemon.is_running()
		if was_running:	self._daemon.stop()
		self._daemon.set_profile(profile_name)
		if was_running: self._daemon.start()

		return True

	@exports.export("", "s")
	def active_profile(self):
		return self._profile

	@exports.export("", "b")
	def status(self):
		return self._daemon.is_running()
