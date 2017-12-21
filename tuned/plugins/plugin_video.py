from . import base
from .decorators import *
import tuned.logs
from tuned.utils.commands import commands
import os
import re

log = tuned.logs.get()

class VideoPlugin(base.Plugin):
	"""
	Plugin for tuning powersave options for some graphic cards.
	"""

	def _init_devices(self):
		self._devices_supported = True
		self._free_devices = set()
		self._assigned_devices = set()

		# FIXME: this is a blind shot, needs testing
		for device in self._hardware_inventory.get_devices("drm").match_sys_name("card*").match_property("DEVTYPE", "drm_minor"):
			self._free_devices.add(device.sys_name)

		self._cmd = commands()

	def _get_device_objects(self, devices):
		return [self._hardware_inventory.get_device("drm", x) for x in devices]

	@classmethod
	def _get_config_options(self):
		return {
			"radeon_powersave" : None,
		}

	def _instance_init(self, instance):
		instance._has_dynamic_tuning = False
		instance._has_static_tuning = True

	def _instance_cleanup(self, instance):
		pass

	def _radeon_powersave_files(self, device):
		return {
			"method" : "/sys/class/drm/%s/device/power_method" % device,
			"profile": "/sys/class/drm/%s/device/power_profile" % device,
			"dpm_state": "/sys/class/drm/%s/device/power_dpm_state" % device
		}

	@command_set("radeon_powersave", per_device=True)
	def _set_radeon_powersave(self, value, device, sim):
		sys_files = self._radeon_powersave_files(device)
		va = str(re.sub(r"(\s*:\s*)|(\s+)|(\s*;\s*)|(\s*,\s*)", " ", value)).split()
		if not os.path.exists(sys_files["method"]):
			if not sim:
				log.warn("radeon_powersave is not supported on '%s'" % device)
				return None
		for v in va:
			if v in ["default", "auto", "low", "mid", "high"]:
				if not sim:
					if (self._cmd.write_to_file(sys_files["method"], "profile") and
						self._cmd.write_to_file(sys_files["profile"], v)):
						return v
			elif v == "dynpm":
				if not sim:
					if (self._cmd.write_to_file(sys_files["method"], "dynpm")):
						return "dynpm"
			# new DPM profiles, recommended to use if supported
			elif v in ["dpm-battery", "dpm-balanced", "dpm-performance"]:
				if not sim:
					state = v[len("dpm-"):]
					if (self._cmd.write_to_file(sys_files["method"], "dpm") and
						self._cmd.write_to_file(sys_files["dpm_state"], state)):
						return v
			else:
				if not sim:
					log.warn("Invalid option for radeon_powersave.")
				return None
		return None

	@command_get("radeon_powersave")
	def _get_radeon_powersave(self, device, ignore_missing = False):
		sys_files = self._radeon_powersave_files(device)
		method = self._cmd.read_file(sys_files["method"], no_error=ignore_missing).strip()
		if method == "profile":
			return self._cmd.read_file(sys_files["profile"]).strip()
		elif method == "dynpm":
			return method
		elif method == "dpm":
			return "dpm-" + self._cmd.read_file(sys_files["dpm_state"]).strip()
		else:
			return None
