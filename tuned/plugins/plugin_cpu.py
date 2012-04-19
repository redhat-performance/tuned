import tuned.plugins
import tuned.logs
import tuned.monitors
import tuned.utils.commands
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

	@classmethod
	def _get_default_options(cls):
		return {
			"load_threshold" : 0.2,
			"latency_low"    : 100,
			"latency_high"   : 1000,
			"cpu_governor"   : "",
		}

	def cleanup(self):
		self._revert_cpu_governor()
		tuned.monitors.get_repository().delete(self._load_monitor)

		os.close(self._cpu_latency_fd)

	def update_tuning(self):
		if not self._commands_run:
			self._apply_cpu_governor()
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

# COMMANDS:

	def _apply_cpu_governor(self):
		self._revert_cpu_governor()

		if len(self._options["cpu_governor"]) == 0:
			return False

		storage = tuned.utils.storage.Storage.get_instance()
		old_value = tuned.utils.commands.execute(["cpupower", "frequency-info", "-p"])
		if old_value.startswith("analyzing CPU"):
			try:
				old_value = old_value.split('\n')[1].split(' ')[2]
				storage.data["cpu"]["cpu_governor"] = old_value
				storage.save()
			except IndexError:
				pass
				

		tuned.utils.commands.execute(["cpupower", "frequency-set", "-g", self._options["cpu_governor"]])
		return True

	def _revert_cpu_governor(self):
		storage = tuned.utils.storage.Storage.get_instance()
		if storage.data["cpu"].has_key("cpu_governor"):
			tuned.utils.commands.execute(["cpupower", "frequency-set", "-g", storage.data["cpu"]["cpu_governor"]])
			del storage.data["cpu"]["cpu_governor"]

		

			