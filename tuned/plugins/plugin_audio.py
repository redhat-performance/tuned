import tuned.plugins
import tuned.logs
import tuned.monitors
from tuned.utils.commands import *
import os
import struct
import glob

log = tuned.logs.get()

STORAGE_CATEGORY = "audio"

class VideoPlugin(tuned.plugins.Plugin):
	"""
	"""

	def __init__(self, devices, options):
		"""
		"""
		super(self.__class__, self).__init__(None, options)

		self._commands_run = False

		if not tuned.utils.storage.Storage.get_instance().data.has_key(STORAGE_CATEGORY):
			tuned.utils.storage.Storage.get_instance().data[STORAGE_CATEGORY] = {}

		self.register_command("enable_ac97_powersave",
								self._set_enable_ac97_powersave,
								self._revert_enable_ac97_powersave)
		self.register_command("hda_intel_powersave",
								self._set_hda_intel_powersave,
								self._revert_hda_intel_powersave)

	@classmethod
	def _get_default_options(cls):
		return {
			"enable_ac97_powersave" : "",
			"hda_intel_powersave" : "",
		}

	def cleanup(self):
		self.cleanup_commands()

	def update_tuning(self):
		if not self._commands_run:
			self.execute_commands()
			self._commands_run = True

	@command(STORAGE_CATEGORY, "enable_ac97_powersave")
	def _set_enable_ac97_powersave(self, value):
		if value == "1" or value == "true":
			value = "Y"
		elif value == "0" or value == "false":
			value = "N"
		else:
			log.warn("Incorrect enable_ac97_powersave value.")
			return ""

		sys_file = "/sys/module/snd_ac97_codec/parameters/power_save"
		if not os.path.exists(sys_file):
			return ""

		old_value = tuned.utils.commands.read_file(sys_file)
		tuned.utils.commands.write_to_file(sys_file, value)
		return old_value

	@command_revert(STORAGE_CATEGORY, "enable_ac97_powersave")
	def _revert_enable_ac97_powersave(self, value):
		sys_file = "/sys/module/snd_ac97_codec/parameters/power_save"
		if not os.path.exists(sys_file):
			return

		tuned.utils.commands.write_to_file(sys_file, value)

	@command(STORAGE_CATEGORY, "hda_intel_powersave")
	def _set_hda_intel_powersave(self, value):
		sys_file = "/sys/module/snd_hda_intel/parameters/power_save"
		if not os.path.exists(sys_file):
			return ""

		old_value = tuned.utils.commands.read_file(sys_file)
		tuned.utils.commands.write_to_file(sys_file, value)
		return old_value

	@command_revert(STORAGE_CATEGORY, "hda_intel_powersave")
	def _revert_hda_intel_powersave(self, value):
		sys_file = "/sys/module/snd_hda_intel/parameters/power_save"
		if not os.path.exists(sys_file):
			return

		tuned.utils.commands.write_to_file(sys_file, value)
