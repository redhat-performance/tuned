import base
import tuned.logs
import tuned.monitors
from decorator import *
import glob
import os
import struct

log = tuned.logs.get()

class CPULatencyPlugin(base.Plugin):
	"""
	Plugin for tuning CPU options. Powersaving, goovernor, required latency, etc.
	"""

	def __init__(self, devices, options):
		super(self.__class__, self).__init__(devices, options)

		self._latency = None
		self._load_monitor = None
		self._cpu_latency_fd = os.open("/dev/cpu_dma_latency", os.O_WRONLY)


	def _delayed_init(self):
		if self._options["force_latency"] is None:
			self._load_monitor = tuned.monitors.get_repository().create("load", self._devices)
			self.update_tuning = self._update_tuning_dynamic
		else:
			self._set_latency(self._options["force_latency"])
			self.update_tuning = self._update_tuning_forced

	@classmethod
	def _get_default_options(cls):
		return {
			"load_threshold"      : 0.2,
			"latency_low"         : 100,
			"latency_high"        : 1000,
			"force_latency"       : None,
			"governor"            : None,
			"multicore_powersave" : None,
		}

	def cleanup(self):
		if self._load_monitor is not None:
			tuned.monitors.get_repository().delete(self._load_monitor)

		os.close(self._cpu_latency_fd)

	def update_tuning(self):
		old_update_tuning = self.update_tuning
		self._delayed_init()
		assert self.update_tuning != old_update_tuning
		self.update_tuning()

	def _update_tuning_forced(self):
		pass

	def _update_tuning_dynamic(self):
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

	@command_set("governor")
	def _set_governor(self, value):
		tuned.utils.commands.execute(["cpupower", "frequency-set", "-g", value])

	@command_get("governor")
	def _get_governor(self):
		old_value = tuned.utils.commands.execute(["cpupower", "frequency-info", "-p"])
		if old_value.startswith("analyzing CPU"):
			try:
				old_value = old_value.split('\n')[1].split(' ')[2]
			except IndexError:
				old_value = ""
				pass
		return old_value

	@command_set("multicore_powersave")
	def _set_multicore_powersave(self, value):
		tuned.utils.commands.execute(["cpupower", "set", "-m", value])

	@command_get("multicore_powersave")
	def _get_multicore_powersave(self):
		old_value = tuned.utils.commands.execute(["cpupower", "info", "-m"])
		if old_value.find("not supported") != -1:
			log.info("cpu_multicore_powersave is not supported by this system")
			return None

		if old_value.startswith("System's multi core scheduler setting"):
			try:
				# get "2\n" and remove '\n'
				old_value = old_value.split(' ')[:-1][:-1]
			except IndexError:
				old_value = None

		return old_value
