from . import base
from .decorators import *
import tuned.logs
from tuned.utils.commands import commands

import os
import struct
import glob

log = tuned.logs.get()
cmd = commands()

class AudioPlugin(base.Plugin):
	"""
	Plugin for tuning audio cards powersaving options.

	Power management is supported per module, not device. From this reason,
	we take kernel module names as device names.
	"""

	def _init_devices(self):
		self._devices_supported = True
		self._assigned_devices = set()
		self._free_devices = set()

		for device in self._hardware_inventory.get_devices("sound").match_sys_name("card*"):
			module_name = self._device_module_name(device)
			if module_name in ["snd_hda_intel", "snd_ac97_codec"]:
				self._free_devices.add(module_name)

	def _instance_init(self, instance):
		instance._has_static_tuning = True
		instance._has_dynamic_tuning = False

	def _instance_cleanup(self, instance):
		pass

	def _device_module_name(self, device):
		try:
			return device.parent.driver
		except:
			return None

	@classmethod
	def _get_config_options(cls):
		return {
			"timeout":          0,
			"reset_controller": False,
		}

	def _timeout_path(self, device):
		return "/sys/module/%s/parameters/power_save" % device

	def _reset_controller_path(self, device):
		return "/sys/module/%s/parameters/power_save_controller" % device

	@command_set("timeout", per_device = True)
	def _set_timeout(self, value, device, sim):
		try:
			timeout = int(value)
		except ValueError:
			log.error("timeout value '%s' is not integer" % value)
			return None
		if timeout >= 0:
			sys_file = self._timeout_path(device)
			if not sim:
				cmd.write_to_file(sys_file, "%d" % timeout)
			return timeout
		else:
			return None

	@command_get("timeout")
	def _get_timeout(self, device, ignore_missing=False):
		sys_file = self._timeout_path(device)
		value = cmd.read_file(sys_file, no_error=ignore_missing)
		if len(value) > 0:
			return value
		return None

	@command_set("reset_controller", per_device = True)
	def _set_reset_controller(self, value, device, sim):
		v = cmd.get_bool(value)
		sys_file = self._reset_controller_path(device)
		if os.path.exists(sys_file):
			if not sim:
				cmd.write_to_file(sys_file, v)
			return v
		return None

	@command_get("reset_controller")
	def _get_reset_controller(self, device, ignore_missing=False):
		sys_file = self._reset_controller_path(device)
		if os.path.exists(sys_file):
			value = cmd.read_file(sys_file)
			if len(value) > 0:
				return cmd.get_bool(value)
		return None
