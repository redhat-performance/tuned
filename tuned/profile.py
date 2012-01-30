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
import units
import utils
import logs
import monitors
import plugins
import threading
import ConfigParser
from subprocess import *

log = logs.get()

class Profile(object):
	def __init__(self, manager, config_file):
		self._manager = manager
		self._config_file = config_file
		self._sysctl = {}
		self._sysctl_original = {}
		self._scripts = []

	def _load_sysctl(self, cfg):
		if cfg.has_section("sysctl"):
			self._sysctl.update(cfg.items("sysctl"))

	def _exec_sysctl(self, data, write = False):
		if write:
			log.debug("Setting sysctl: %s" % (data))
			proc = Popen(["/sbin/sysctl", "-q", "-w", data], stdout=PIPE, stderr=PIPE)
		else:
			proc = Popen(["/sbin/sysctl", "-e", data], stdout=PIPE, stderr=PIPE)
		out, err = proc.communicate()

		if proc.returncode:
			log.error("sysctl error: %s" % (err[:-1]))
		return (proc.returncode, out, err)

	def _apply_sysctl(self):
		for key, value in self._sysctl.iteritems():
			returncode, out, err = self._exec_sysctl(key)
			if not returncode:
				k = out.split('=')[0].strip()
				v = out.split('=')[1].strip()
				self._sysctl_original[k] = v

			self._exec_sysctl(key + "=" + value, True)
		return True

	def _revert_sysctl(self):
		for key, value in self._sysctl_original.iteritems():
			self._exec_sysctl(key + "=" + value, True)

	def _call_scripts(self, arg = "start"):
		for script in self._scripts:
			try: 
				proc = Popen([script, arg], stdout=PIPE, stderr=PIPE)
				out, err = proc.communicate()

				if proc.returncode:
					log.error("script %s error: %s" % (script, err[:-1]))
			except OSError as e:
				log.error("Script %s error: %s" % (script, e))
		return True

	def _load_config(self, manager, config):
		if not os.path.exists(config):
			log.error("Config file %s does not exist" % (config))
			return False

		cfg = ConfigParser.SafeConfigParser()
		cfg.read(config)

		if cfg.has_option("main", "include"):
			self._load_config(manager, cfg.get("main", "include"))

		if cfg.has_option("main", "script"):
			script = os.path.abspath(cfg.get("main", "script"))
			if not script in self._scripts:
				self._scripts.append(script)

		self._load_sysctl(cfg)

		for section in cfg.sections():
			if section in ["main", "sysctl"]:
				continue

			if not cfg.has_option(section, "type"):
				log.error("No 'type' option for %s plugin" % (section))
				continue

			plugin = cfg.get(section, "type")
			plugin_cfg = dict(cfg.items(section))
			del plugin_cfg["type"]

			p = manager.create(section, plugin, plugin_cfg)

		return True

	def load(self):
		return self._load_config(self._manager, self._config_file) and self._apply_sysctl() and self._call_scripts()

	def cleanup(self):
		self._revert_sysctl()
		self._call_scripts("stop")
