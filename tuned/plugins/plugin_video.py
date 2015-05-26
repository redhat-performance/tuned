import base
from decorators import *
import tuned.logs
from tuned.utils.commands import commands
import os

log = tuned.logs.get()

class VideoPlugin(base.Plugin):
	"""
	Plugin for tuning powersave options for some graphic cards.
	"""

	def _init_devices(self):
		self._devices = set()
		self._assigned_devices = set()

		# FIXME: this is a blind shot, needs testing
		for device in self._hardware_inventory.get_devices("drm").match_sys_name("card*").match_property("DEVTYPE", "drm_minor"):
			self._devices.add(device.sys_name)

		self._free_devices = self._devices.copy()
		self._cmd = commands()

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
		}

	@command_set("radeon_powersave", per_device=True)
	def _set_radeon_powersave(self, value, device, sim):
		sys_files = self._radeon_powersave_files(device)
		if not os.path.exists(sys_files["method"]):
			if not sim:
				log.warn("radeon_powersave is not supported on '%s'" % device)
			return None

		if value in ["default", "auto", "low", "mid", "high"]:
			if not sim:
				self._cmd.write_to_file(sys_files["method"], "profile")
				self._cmd.write_to_file(sys_files["profile"], value)
			return value
		elif value == "dynpm":
			if not sim:
				self._cmd.write_to_file(sys_files["method"], "dynpm")
			return "dynpm"
		else:
			if not sim:
				log.warn("Invalid option for radeon_powersave.")
			return None


	@command_get("radeon_powersave")
	def _get_radeon_powersave(self, device):
		sys_files = self._radeon_powersave_files(device)
		method = self._cmd.read_file(sys_files["method"]).strip()
		if method == "profile":
			return self._cmd.read_file(sys_files["profile"]).strip()
		elif method == "dynpm":
			return "dynpm"
		else:
			 return None
