import tuned.plugins
import tuned.logs
import tuned.monitors
import os
import struct

log = tuned.logs.get()

class EeePCSHEPlugin(tuned.plugins.Plugin):
	"""
	"""

	def __init__(self, devices, options):
		"""
		"""
		super(self.__class__, self).__init__(None, options)

		self._she_mode = None
		self._load_monitor = tuned.monitors.get_repository().create("load", devices)
		try:
			os.open("/sys/devices/platform/eeepc/cpufv", os.O_WRONLY)
		except:
			log.info("eeepc_she is not supported on you system")
			raise

	@classmethod
	def _get_default_options(cls):
		return {
			"load_threshold_normal"    : 0.6,
			"load_threshold_powersave" : 0.4,
			"she_powersave"            : 2,
			"she_normal"               : 1,
		}

	def cleanup(self):
		tuned.monitors.get_repository().delete(self._load_monitor)

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
			try:
				os.open("/sys/devices/platform/eeepc/cpufv", os.O_WRONLY).write(str(she_mode) + "\n")
			except:
				pass
			self._she_mode = she_mode
