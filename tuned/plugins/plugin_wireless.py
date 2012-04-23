import tuned.plugins
import tuned.logs
import tuned.monitors
import tuned.utils.commands
import os
import struct

log = tuned.logs.get()

class WirelessPlugin(tuned.plugins.Plugin):
	"""
	"""

	def __init__(self, devices, options):
		"""
		"""
		super(self.__class__, self).__init__(None, options)

		self._commands_run = False

		if not tuned.utils.storage.Storage.get_instance().data.has_key("wireless"):
			tuned.utils.storage.Storage.get_instance().data["wireless"] = {}

	@classmethod
	def _get_default_options(cls):
		return {
			"wifi_power_level" : "",
		}

	def cleanup(self):
		self._revert_wifi_power_level()

	def update_tuning(self):
		if not self._commands_run:
			self._apply_wifi_power_level()
			self._commands_run = True

# COMMANDS:

	def _apply_wifi_power_level(self):
		self._revert_wifi_power_level()

		if len(self._options["wifi_power_level"]) == 0:
			return False

		return True

	def _revert_wifi_power_level(self):
		#storage = tuned.utils.storage.Storage.get_instance()
		#if storage.data["cpu"].has_key("cpu_governor"):
			#tuned.utils.commands.execute(["cpupower", "frequency-set", "-g", storage.data["cpu"]["cpu_governor"]])
			#del storage.data["cpu"]["cpu_governor"]
