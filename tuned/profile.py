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
import pprint

import tuned.plugins

log = logs.get()

class Profile(object):
	def __init__(self, manager, config_file):
		self._manager = manager
		self._config_file = config_file
		self._plugin_configs = {}

	@classmethod
	def find_profile(cls, name):
		if name.startswith("/"):
			return name

		profile = "/etc/tuned/%s/tuned.conf" % (name)
		if os.path.exists(profile):
			return profile

		profile = "/usr/lib/tuned/%s/tuned.conf" % (name)
		if os.path.exists(profile):
			return profile

		return name

	def _disable_plugin(self, name, plugin_cfg):
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
						log.debug("Disabling plugin %s device %s" % (plugin, device))
				# If we removed all devices, this plugin is not useful anymore,
				# so we should remove it too:
				if (len(cfg["devices"]) == 0):
					plugins_to_remove.append(plugin)
			else:
				# If the plugin does not have any device set, it can be
				# run only once, so remove previous occurence
				log.debug("Disabling plugin %s" % (plugin))
				plugins_to_remove.append(plugin)

		for plugin in plugins_to_remove:
			log.debug("Removing plugin %s because it is useless after disabling" % (plugin))
			del self._plugin_configs[plugin]

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
				# If the plugin does not have any device set, it can be
				# run only once, so remove previous occurence
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

		# Check if the plugin is supported on this HW
		if not tuned.plugins.get_repository().is_supported(plugin):
			log.info("Plugin %s is not supported on this HW" % (plugin))
			return

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

		if plugin_cfg.has_key("disable"):
			self._disable_plugin(name, plugin_cfg)
			return

		if plugin_cfg.has_key("replace"):
			self._replace_plugin(name, plugin_cfg)
			del plugin_cfg["replace"]
		else:
			self._merge_plugin(name, plugin_cfg)
		self._plugin_configs[name] = plugin_cfg

	def _apply_config(self):
		pp = pprint.PrettyPrinter(indent=4)
		log.debug("Loaded config: %s" % (pp.pformat(self._plugin_configs)))

		for name, cfg in self._plugin_configs.iteritems():
			plugin = cfg["type"]
			del cfg["type"]
			p = self._manager.create(name, plugin, cfg)

	def _get_unique_name(self, name):
		i = 1
		n = name
		while n in self._plugin_configs.keys():
			n = name + "_" + str(i)
			i += 1
		return n

	def _load_config(self, manager, config):
		if not os.path.exists(config):
			log.error("Config file %s does not exist" % (config))
			return False

		cfg = ConfigParser.SafeConfigParser()
		cfg.read(config)

		if cfg.has_option("main", "include"):
			included_cfg = self.find_profile(cfg.get("main", "include"))
			self._load_config(manager, included_cfg)

		for section in cfg.sections():
			if section == "main":
				continue
			if not cfg.has_option(section, "type"):
				log.info("No 'type' option for %s plugin, will treat '%s' as a plugin type" % (section, section))
				cfg.set(section, "type", section)
			cfg.set(section, "_load_path", os.path.dirname(config))

			self._store_plugin_config(self._get_unique_name(section), dict(cfg.items(section)))

		return True

	def load(self):
		return (self._load_config(self._manager, self._config_file) and
			self._apply_config())

	def cleanup(self):
		pass
