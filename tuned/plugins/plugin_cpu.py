import tuned.plugins
import tuned.logs
import tuned.monitors
from tuned.utils.commands import *
import os
import struct

log = tuned.logs.get()

class CPULatencyPlugin(tuned.plugins.Plugin):
	"""
	"""

	def __init__(self, devices, options):
		"""
		"""
		super(self.__class__, self).__init__(None, options)

		self._latency = None
		self._cpu_latency_fd = os.open("/dev/cpu_dma_latency", os.O_WRONLY)
		self._load_monitor = tuned.monitors.get_repository().create("load", devices)
		self._commands_run = False

		if not tuned.utils.storage.Storage.get_instance().data.has_key("cpu"):
			tuned.utils.storage.Storage.get_instance().data["cpu"] = {}

		self.register_command("cpu_governor",
								self._set_cpu_governor,
								self._revert_cpu_governor)
		self.register_command("cpu_multicore_powersave",
								self._set_cpu_multicore_powersave,
								self._revert_cpu_multicore_powersave)

	@classmethod
	def _get_default_options(cls):
		return {
			"load_threshold" : 0.2,
			"latency_low"    : 100,
			"latency_high"   : 1000,
			"cpu_governor"   : "",
			"cpu_multicore_powersave" : "",
		}

	def cleanup(self):
		self.cleanup_commands()
		tuned.monitors.get_repository().delete(self._load_monitor)

		os.close(self._cpu_latency_fd)

	def update_tuning(self):
		if not self._commands_run:
			self.execute_commands()
			self._commands_run = True

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
