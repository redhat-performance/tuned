import tuned.plugins
import tuned.monitors
import os
import struct

class CPULatencyPlugin(tuned.plugins.Plugin):
	"""
	"""

	def __init__(self, devices = None, options = None):
		"""
		"""
		super(self.__class__, self).__init__(options, None, options)

		self._latency = None
		self._cpu_latency_fd = os.open("/dev/cpu_dma_latency", os.O_WRONLY)
		self._load_monitor = tuned.monitors.get_repository().create("load", devices)

	@classmethod
	def _get_default_options(cls):
		return {
			"load_threshold" : 0.2,
			"latency_low"    : 100,
			"latency_high"   : 1000,
		}

	def cleanup(self):
		os.close(self._cpu_latency_fd)

	def update_tuning(self):
		load = self._load_monitor.get_load()["system"]
		if load < self._options["load_threshold"]:
			self._set_latency(self._options["latency_high"])
		else:
			self._set_latency(self._options["latency_low"])

	def _set_latency(self, latency):
		if self._latency != latency:
			latency_bin = struct.pack("i", int(latency))
			os.write(self._cpu_latency_fd, latency_bin)
