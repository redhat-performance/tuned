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
import glob
from subprocess import *

import tuned.plugins

log = logs.get()

class Profile(object):
	def __init__(self, manager, config_file):
		self._manager = manager
		self._config_file = config_file
		self._scripts = []
		self._elevator = ""
		# TODO: match cciss* somehow
		self._elevator_devs = "/sys/block/sd*/queue/scheduler"
		self._plugin_configs = {}

	def _load_ktuned(self):
		for cfg in glob.glob("/etc/ktune.d/*.conf"):
			f = open(os.path.join("/etc/ktune.d/", cfg))
			for line in f.readlines():
				if not line.strip().startswith("#") and line.find("=") != -1:
					k = out.split('=')[0].strip()
					v = out.split('=')[1].strip()
					self._sysctl[k] = v
			f.close()
		for sh in glob.glob("/etc/ktune.d/*.sh"):
			script = os.path.join("/etc/ktune.d/", sh)
			if not script in self._scripts:
				self._scripts.append(script)
		return True

	def _apply_elevator(self):
		for dev in glob.glob(self._elevator_devs):
			log.debug("Applying elevator: %s < %s" % (dev, self._elevator))
			try:
				f = open(dev, "w")
				f.write(self._elevator)
				f.close()
			except (OSError,IOError) as e:
				log.error("Setting elevator on %s error: %s" % (dev, e))
		return True

	def _revert_elevator(self):
		for dev in glob.glob(self._elevator_devs):
			log.debug("Applying elevator: %s < cfs" % (dev))
			try:
				f = open(dev, "w")
				f.write("cfs")
				f.close()
			except (OSError,IOError) as e:
				log.error("Setting elevator on %s error: %s" % (dev, e))

	def _call_scripts(self, arg = "start"):
		for script in self._scripts:
			log.info("Calling script %s" % (script))
			try:
				proc = Popen([script, arg], stdout=PIPE, stderr=PIPE)
				out, err = proc.communicate()

				if proc.returncode:
					log.error("script %s error: %s" % (script, err[:-1]))
			except (OSError,IOError) as e:
				log.error("Script %s error: %s" % (script, e))
		return True

	def _replace_plugin(self, name, plugin_cfg):
		# Iterates over already loaded plugins.
		# If the already loaded plugin contains the same device as the newly
		# loaded one, remove the device from the already loaded one.
		plugins_to_remove = []
		for plugin, cfg in self._plugin_configs.iteritems():
			if cfg["type"] != plugin_cfg["type"]:
				continue

			if cfg.has_key("devices") and cfg["devices"] != None:
				for device in plugin_cfg["devices"]:
					if device in cfg["devices"]:
						cfg["devices"].remove(device)
						log.debug("Replacing plugin %s device %s by %s" % (plugin, device, name))
				# If we removed all devices, this plugin is not useful anymore,
				# so we should remove it too:
				if (len(cfg["devices"]) == 0):
					plugins_to_remove.append(plugin)
			else:
				log.debug("Replacing plugin %s by %s" % (plugin, name))
				plugins_to_remove.append(plugin)

		for plugin in plugins_to_remove:
			log.debug("Removing plugin %s because it is useless after replace" % (plugin))
			del self._plugin_configs[plugin]

	def _merge_plugin(self, name, plugin_cfg):
		# Iterates over already loaded plugins.
		# Merges the option of two plugins with the same types together
		plugins_to_remove = []
		for plugin, cfg in self._plugin_configs.iteritems():
			if cfg["type"] != plugin_cfg["type"]:
				continue

			if cfg.has_key("devices") and cfg["devices"] != None:
				for device in plugin_cfg["devices"]:
					if device in cfg["devices"]:
						log.debug("Merging plugin %s with %s" % (name, plugin))
						plugin_cfg.update(cfg)
						plugins_to_remove.append(plugin)
						break
			else:
				log.debug("Merging plugin %s with %s" % (name, plugin))
				plugin_cfg.update(cfg)
				plugins_to_remove.append(plugin)
				
		for plugin in plugins_to_remove:
			log.debug("Removing plugin %s because it is useless after merge" % (plugin))
			del self._plugin_configs[plugin]

	def _store_plugin_config(self, name, plugin_cfg):
		plugin = plugin_cfg["type"]
		# If there are no devices set, set all tunable_devices as default
		if not plugin_cfg.has_key("devices"):
			try:
				plugin_cfg["devices"] = tuned.plugins.get_repository().tunable_devices(plugin)
			except tuned.exceptions.TunedException as e:
				e.log()
				log.error("unable to create unit %s" % plugin)
				return
		else:
			plugin_cfg["devices"] = plugin_cfg["devices"].split(",")

		if plugin_cfg.has_key("merge"):
			self._merge_plugin(name, plugin_cfg)
			del plugin_cfg["merge"]
		else:
			self._replace_plugin(name, plugin_cfg)
		self._plugin_configs[name] = plugin_cfg

	def _apply_config(self):
		for name, cfg in self._plugin_configs.iteritems():
			plugin = cfg["type"]
			del cfg["type"]
			p = self._manager.create(name, plugin, cfg)

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

		if cfg.has_option("main", "elevator"):
			self._elevator = cfg.get("main", "elevator")

		if cfg.has_option("main", "elevator_tune_devs"):
			self._elevator_devs = cfg.get("main", "elevator_tune_devs")

		for section in cfg.sections():
			if not cfg.has_option(section, "type"):
				log.error("No 'type' option for %s plugin" % (section))
				continue

			self._store_plugin_config(section, dict(cfg.items(section)))

		return True

	def load(self):
		return (self._load_config(self._manager, self._config_file) and
			self._apply_config() and self._load_ktuned() and
			self._apply_elevator() and self._call_scripts())

	def cleanup(self):
		self._revert_elevator()
		self._call_scripts("stop")
