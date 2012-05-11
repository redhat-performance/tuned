import tuned.plugins
import tuned.logs
import tuned.monitors
from tuned.plugins.decorator import *
import os
import struct
import glob

log = tuned.logs.get()

class VideoPlugin(tuned.plugins.Plugin):
	"""
	"""

	@classmethod
	def _get_default_options(cls):
		return {
			"ac97_powersave"      : None,
			"hda_intel_powersave" : None,
			"dynamic_tuning"      : False,
		}

	def cleanup(self):
		pass

	def update_tuning(self):
		pass

	@command_set("ac97_powersave")
	def _set_ac97_powersave(self, value):
		if value == "1" or value == "true":
			value = "Y"
		elif value == "0" or value == "false":
			value = "N"
		else:
			log.warn("Incorrect ac97_powersave value.")
			return

		sys_file = "/sys/module/snd_ac97_codec/parameters/power_save"
		if not os.path.exists(sys_file):
			return
		tuned.utils.commands.write_to_file(sys_file, value)

	@command_get("ac97_powersave")
	def _get_ac97_powersave(self, value):
		sys_file = "/sys/module/snd_ac97_codec/parameters/power_save"
		if not os.path.exists(sys_file):
			return None
		return tuned.utils.commands.read_file(sys_file)

	@command_set("hda_intel_powersave")
	def _set_hda_intel_powersave(self, value):
		sys_file = "/sys/module/snd_hda_intel/parameters/power_save"
		if not os.path.exists(sys_file):
			return
		tuned.utils.commands.write_to_file(sys_file, value)

	@command_get("hda_intel_powersave")
	def _revert_hda_intel_powersave(self, value):
		sys_file = "/sys/module/snd_hda_intel/parameters/power_save"
		if not os.path.exists(sys_file):
			return None
		return tuned.utils.commands.read_file(sys_file)
