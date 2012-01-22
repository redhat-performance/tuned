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

import units
import utils
import logs
import monitors
import plugins
import threading

log = logs.get()

DEFAULT_CONFIG_FILE = "/etc/tuned/tuned.conf"

class Daemon(object):
	def __init__(self, config_file = None):
		log.info("initializing Daemon")
		if config_file is None:
			config_file = DEFAULT_CONFIG_FILE
		self._config_file = config_file

		self._thread = None
		self._terminate = threading.Event()

	def _thread_code(self):
		self._terminate.clear()

		# TODO: temporary code
		manager = units.get_manager()
		monitors_repo = monitors.get_repository()
		plugins_repo = plugins.get_repository()

		test_a = manager.create("test", "test", None)
		test_b = manager.create("foo", "cpu", None)

		while not self._terminate.wait(10):
			log.debug("updating monitors")
			monitors_repo.update()
			log.debug("performing tunings")
			plugins_repo.update()

		manager.delete_all()

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
