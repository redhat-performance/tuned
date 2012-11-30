import base
import os.path
import tuned.logs
import tuned.utils.commands
import os

log = tuned.logs.get()

class EeePCSHEPlugin(base.Plugin):
	"""
	Plugin for tuning FSB (front side bus) speed on Asus EEE PCs with SHE (Super Hybrid Engine) support.
	"""

	def _post_init(self):
		self._she_mode = None
		self._load_monitor = None
		self._load_monitor = self._monitors_repository.create("load", devices)

	@classmethod
	def tunable_devices(self):
		return ["she"]

	@classmethod
	def is_supported(cls):
		return os.path.isfile(EeePCSHEPlugin._she_control_file())

	@classmethod
	def _get_default_options(cls):
		return {
			"load_threshold_normal"    : 0.6,
			"load_threshold_powersave" : 0.4,
			"she_powersave"            : 2,
			"she_normal"               : 1,
		}

	@classmethod
	def _she_control_file(self):
		return "/sys/devices/platform/eeepc/cpufv"

	def cleanup(self):
		if self._load_monitor:
			self._monitors_repository.delete(self._load_monitor)

	def update_tuning(self):
		load = self._load_monitor.get_load()["system"]
		if load <= self._options["load_threshold_powersave"]:
			self._set_she_mode(self._options["she_powersave"])
		elif load >= self._options["load_threshold_normal"]:
			self._set_she_mode(self._options["she_normal"])

	def _lookup_she(self, she_mode):
		if she_mode == self._options["she_powersave"]:
			return "powersave"
		elif she_mode == self._options["she_normal"]:
			return "normal"
		return str(she_mode)

	def _set_she_mode(self, she_mode):
		she_mode = int(she_mode)
		if self._she_mode != she_mode:
			log.info("new eeepc_she mode %s" % self._lookup_she(she_mode))
			tuned.utils.commands.write_to_file(EeePCSHEPlugin._she_control_file(), str(she_mode) + "\n")
			self._she_mode = she_mode
