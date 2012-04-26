import tuned.plugins
import tuned.logs
import tuned.monitors
from tuned.utils.commands import *
import os
import struct
import glob

log = tuned.logs.get()

class CPULatencyPlugin(tuned.plugins.Plugin):
	"""
	"""

	def __init__(self, devices, options):
		"""
		"""
		super(self.__class__, self).__init__(devices, options)

		self._latency = None
		self._cpu_latency_fd = os.open("/dev/cpu_dma_latency", os.O_WRONLY)

		self.dynamic_tuning = None
		if self.dynamic_tuning:
			self._load_monitor = tuned.monitors.get_repository().create("load", devices)

		if not tuned.utils.storage.Storage.get_instance().data.has_key("cpu"):
			tuned.utils.storage.Storage.get_instance().data["cpu"] = {}

		self.register_command("cpu_governor",
								self._set_cpu_governor,
								self._revert_cpu_governor)
		self.register_command("cpu_multicore_powersave",
								self._set_cpu_multicore_powersave,
								self._revert_cpu_multicore_powersave)
		self.register_command("enable_usb_autosupend",
								self._set_enable_usb_autosupend,
								self._revert_enable_usb_autosupend)

	@classmethod
	def _get_default_options(cls):
		return {
			"load_threshold" : 0.2,
			"latency_low"    : 100,
			"latency_high"   : 1000,
			"cpu_governor"   : "",
			"cpu_multicore_powersave" : "",
			"enable_usb_autosupend" : "",
		}

	def cleanup(self):
		if self._load_monitor:
			tuned.monitors.get_repository().delete(self._load_monitor)

		os.close(self._cpu_latency_fd)

	def update_tuning(self):
		load = self._load_monitor.get_load()["system"]
		if load < self._options["load_threshold"]:
			self._set_latency(self._options["latency_high"])
		else:
			self._set_latency(self._options["latency_low"])

	def _set_latency(self, latency):
		latency = int(latency)
		if self._latency != latency:
			log.info("new cpu latency %d" % latency)
			latency_bin = struct.pack("i", latency)
			os.write(self._cpu_latency_fd, latency_bin)
			self._latency = latency

	@command("cpu", "cpu_governor")
	def _set_cpu_governor(self, value):
		old_value = tuned.utils.commands.execute(["cpupower", "frequency-info", "-p"])
		if old_value.startswith("analyzing CPU"):
			try:
				old_value = old_value.split('\n')[1].split(' ')[2]
			except IndexError:
				old_value = ""
				pass

		tuned.utils.commands.execute(["cpupower", "frequency-set", "-g", value])
		return old_value

	@command_revert("cpu", "cpu_governor")
	def _revert_cpu_governor(self, value):
		tuned.utils.commands.execute(["cpupower", "frequency-set", "-g", value])

	@command("cpu", "cpu_multicore_powersave")
	def _set_cpu_multicore_powersave(self, value):
		old_value = tuned.utils.commands.execute(["cpupower", "info", "-m"])
		if old_value.find("not supported") != -1:
			log.info("cpu_multicore_powersave is not supported by this system")
			return ""

		if old_value.startswith("System's multi core scheduler setting"):
			try:
				old_value = old_value.split(' ')[:-1][:-1] # get "2\n" and remove '\n'
			except IndexError:
				old_value = ""

		tuned.utils.commands.execute(["cpupower", "set", "-m", value])
		return old_value

	@command_revert("cpu", "cpu_multicore_powersave")
	def _revert_cpu_multicore_powersave(self, value):
		tuned.utils.commands.execute(["cpupower", "set", "-m", value])

	#TODO: Move USB to different plugin, I'm just not sure which one...
	@command("cpu", "enable_usb_autosupend")
	def _set_enable_usb_autosupend(self, value):
		old_value = {}
		if value == "1" or value == "true":
			value = "1"
		elif value == "0" or value == "false":
			value = "0"
		else:
			log.warn("Incorrect enable_bluetooth value.")
			return ""
		for sys_file in glob.glob("/sys/bus/usb/devices/*/power/autosuspend"):
			old_value[sys_file] = tuned.utils.commands.read_file(sys_file)
			tuned.utils.commands.write_to_file(sys_file, value)

		return old_value

	@command_revert("cpu", "enable_usb_autosupend")
	def _revert_enable_usb_autosupend(self, values):
		for sys_file, value in values.iteritems():
			tuned.utils.commands.write_to_file(sys_file, value)
