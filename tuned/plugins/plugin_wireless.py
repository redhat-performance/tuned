import tuned.plugins
import tuned.logs
import tuned.monitors
import tuned.utils.commands
import os
import struct
import glob

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

	def _set_wifi_power_level(self, power_level):
		try:
			lines = open("/proc/net/wireless").readlines()
		except (OSError,IOError) as e:
			log.error("Error reading wifi devices from /proc/net/wireless: %s" % (e))
			return None

		ifaces = []
		for line in lines:
			if line.find("|") != -1:
				continue
			try:
				ifaces.append(line[:line.find(":")])
			except IndexError:
				pass

		if len(ifaces) == 0:
			log.info("No wifi interfaces found")
			return None

		# TODO: set old_value properly. Is there "get_power"? I don't have wifi here
		old_value = "5"

		for iface in ifaces:
			tuned.utils.commands.execute(["iwpriv", iface, "set_power", power_level])

		for sys_file in glob.glob("/sys/bus/pci/devices/*/power_level"):
			tuned.utils.commands.write_to_file(sys_file, power_level)

		return old_value

	def _apply_wifi_power_level(self):
		self._revert_wifi_power_level()

		if len(self._options["wifi_power_level"]) == 0:
			return False

		old_value = self._set_wifi_power_level(self._options["wifi_power_level"])
		if old_value:
			storage = tuned.utils.storage.Storage.get_instance()
			storage.data["wireless"]["wifi_power_level"] = old_value
			storage.save()

		return True

	def _revert_wifi_power_level(self):
		storage = tuned.utils.storage.Storage.get_instance()
		if storage.data["wireless"].has_key("wifi_power_level"):
			self._set_wifi_power_level(storage.data["wireless"]["wifi_power_level"])
			del storage.data["wireless"]["wifi_power_level"]
