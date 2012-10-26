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

import os
import threading
import logs

log = logs.get()

ACTIVE_PROFILE_FILENAME = "/etc/tuned/saved_profile"
DEFAULT_PROFILE_NAME = "balanced"

class Daemon(object):
	def __init__(self, unit_manager, profile_loader, profile_name=None):
		log.debug("initializing daemon")
		self._unit_manager = unit_manager
		self._profile_loader = profile_loader
		self._thread = None
		self._terminate = threading.Event()

		if profile_name is None:
			profile_name = self.get_active_profile()
		self.set_profile(profile_name)

	def set_profile(self, profile_name):
		if self.is_running():
			raise Exception("Cannot set profile while the daemon is running.")
		self._profile = self._profile_loader.load(profile_name)

	def _thread_code(self):
		if self._profile is None:
			raise Exception("Cannot start the daemon without setting a profile.")

		self._unit_manager.create(self._profile.units)
		self.save_active_profile()

		self._unit_manager.plugins_repository.do_static_tuning()

		self._terminate.clear()
		while not self._terminate.wait(10):
			log.debug("updating monitors")
			self._unit_manager.monitors_repository.update()
			log.debug("performing tunings")
			self._unit_manager.plugins_repository.update()

		self._unit_manager.delete_all()

	def save_active_profile(self):
		try:
			with open(ACTIVE_PROFILE_FILENAME, "w") as f:
				f.write(self._profile.name)
		except (OSError,IOError) as e:
			log.error("Cannot write active profile into %s: %s" % (ACTIVE_PROFILE_FILENAME, e))

	def get_active_profile(self):
		try:
			with open(ACTIVE_PROFILE_FILENAME, "r") as f:
				return f.read().strip()
		except (OSError, IOError, EOFError) as e:
			log.error("Cannot read active profile, setting default.")
			return DEFAULT_PROFILE_NAME

	@property
	def config_file(self):
		return self._config_file

	@config_file.setter
	def config_file(self, value):
		if not isinstance(value, list):
			value = [value]
		for cfg in value:
			if not os.path.exists(cfg):
				raise ValueError("Config file %s does not exist" % (cfg))

		self._config_file = value
		# TODO: Maybe restart the daemon here?

	def is_running(self):
		return self._thread is not None and self._thread.is_alive()

	def is_enabled(self):
		# TODO
		return True

	def start(self):
		if self.is_running():
			return False
		log.info("starting tuning")
		self._thread = threading.Thread(target=self._thread_code)
		self._thread.start()
		return True

	def stop(self):
		if not self.is_running():
			return False
		log.info("stopping tunning")
		self._terminate.set()
		self._thread.join()
		self._thread = None

		return True

	def cleanup(self):
		# TODO: do we need it?
		pass
