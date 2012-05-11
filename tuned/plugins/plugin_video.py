import tuned.plugins
import tuned.logs
import tuned.monitors
from tuned.utils.commands import *
import glob
import os
import struct

log = tuned.logs.get()

class VideoPlugin(tuned.plugins.Plugin):
	"""
	Plugin for tuning powersave options for some graphic cards.
	"""

	@classmethod
	def _get_default_options(cls):
		return {
			"dynamic_tuning"   : "0",
			"radeon_powersave" : None,
		}

	@classmethod
	def tunable_devices(cls):
		# radeon_powersave is currently the only condition
		config_files = glob.glob("/sys/class/drm/*/device/power_method")
		available = set(map(lambda name: name.split("/")[4], config_files))
		return available

	def cleanup(self):
		pass

	def update_tuning(self):
		pass

	def _radeon_powersave_files(self, device):
		return {
			"method" : "/sys/class/drm/%s/device/power_method" % device,
			"profile": "/sys/class/drm/%s/device/power_profile" % device,
		]

	@command_set("radeon_powersave", per_device=True)
	def _set_radeon_powersave(self, value, device):
		sys_files = self._radeon_powersave_files(device)
		if value in ["default", "auto", "low", "med", "high"]:
			tuned.utils.commands.write_to_file(sys_files["method"], "profile")
			tuned.utils.commands.write_to_file(sys_files["profile"], value)
		elif value == "dynpm":
			tuned.utils.commands.write_to_file(sys_files["method"], "dynpm")
		else:
			log.warn("Invalid option for radeon_powersave.")

	@command_get("radeon_powersave")
	def _get_radeon_powersave(self, device):
		sys_files = self._radeon_powersave_files(device)
		return tuned.utils.commands.read_file(sys_files["profile"])
