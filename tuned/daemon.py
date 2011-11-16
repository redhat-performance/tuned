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

import utils
import logs

log = logs.get("tuned")

CONFIG_FILE = "/etc/tuned/tuned.conf"
INIT_TIMEOUT = 3

class Daemon(object):
	def __init__(self, config_file = None):
		log.info("initializing")
		if config_file is None:
			config_file = CONFIG_FILE
		self._config_file = config_file

	def run(self):
		log.info("running")

		import time

		self._terminate = False
		while not self._terminate:
			time.sleep(1)

	def terminate(self):
		log.info("terminating")
		self._terminate = True

	def reload(self):
		log.info("reloading")
		pass

	def cleanup(self):
		# TODO: do we need it?
		pass
