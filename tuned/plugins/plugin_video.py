import tuned.plugins
import tuned.logs
import tuned.monitors
from tuned.utils.commands import *
import os
import struct
import glob

log = tuned.logs.get()

STORAGE_CATEGORY = "video"

class VideoPlugin(tuned.plugins.Plugin):
	"""
	"""

	def __init__(self, devices, options):
		"""
		"""
		super(self.__class__, self).__init__(devices, options)

		if not tuned.utils.storage.Storage.get_instance().data.has_key(STORAGE_CATEGORY):
			tuned.utils.storage.Storage.get_instance().data[STORAGE_CATEGORY] = {}

		self.register_command("radeon_powersave",
								self._set_radeon_powersave,
								self._revert_radeon_powersave)

	@classmethod
	def _get_default_options(cls):
		return {
			"dynamic_tuning" : "0",
			"radeon_powersave" : "",
		}

	def cleanup(self):
		pass

	def update_tuning(self):
		pass

	@command(STORAGE_CATEGORY, "radeon_powersave")
	def _set_radeon_powersave(self, value):
		if not os.path.exists("/sys/class/drm/card0/device/power_method"):
			return ""

		old_values = []
		if value in ["default", "auto", "low", "med", "high"]:
			power_profile = tuned.utils.commands.read_file("/sys/class/drm/card0/device/power_profile")
			power_method = tuned.utils.commands.read_file("/sys/class/drm/card0/device/power_method")
			old_values = [power_profile, power_method]
			
			tuned.utils.commands.write_to_file("/sys/class/drm/card0/device/power_method", "profile")
			tuned.utils.commands.write_to_file("/sys/class/drm/card0/device/power_profile", value)
		elif value == "dynpm":
			power_profile = tuned.utils.commands.read_file("/sys/class/drm/card0/device/power_profile")
			power_method = tuned.utils.commands.read_file("/sys/class/drm/card0/device/power_method")
			old_values = [None, power_method]
			
			tuned.utils.commands.write_to_file("/sys/class/drm/card0/device/power_method", "dynpm")
		return old_values

	@command_revert(STORAGE_CATEGORY, "radeon_powersave")
	def _revert_radeon_powersave(self, values):
		power_profile, power_method = values

		tuned.utils.commands.write_to_file("/sys/class/drm/card0/device/power_method", power_method)
		if power_profile:
			tuned.utils.commands.write_to_file("/sys/class/drm/card0/device/power_profile", power_profile)
