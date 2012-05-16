import tuned.plugins
import tuned.log
from tuned.utils.commands import *
import glob

log = tuned.log.get()

class USBPlugin(tuned.plugins.Plugin):
	"""
	Plugin for tuning various options of USB subsystem.
	"""

	@classmethod
	def _get_default_options(cls):
		return {
			"autosuspend" : None,
		}

	@classmethod
	def tunable_devices(cls):
		control_files = glob.glob("/sys/bus/usb/devices/*/power/control")
		available = set(map(lambda name: name.split("/")[5], control_files))
		return available

	def update_tuning(self):
		# FIXME: can we drop this method?
		pass

	def _autosuspend_sysfile(self, device):
		return "/sys/bus/usb/devices/%s/power/autosuspend" % device

	@command_set("autosuspend", per_device=True)
	def _set_autosuspend(self, value, device):
		value = self._config_bool(value)
		if value is None:
			log.warn("Invalid value for USB autosuspend.")

		sys_file = self._autosuspend_sysfile(device)
		tuned.utils.commands.write_to_file(sys_file, value)

	@command_get("autosuspend")
	def _get_autosuspend(self, device):
		sys_file = self._autosuspend_sysfile(device)
		return tuned.utils.commands.read_file(sys_file)
