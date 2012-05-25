import base
from decorators import *
import tuned.logs
import tuned.utils.commands

import fnmatch
import os
import struct

log = tuned.logs.get()

class CPULatencyPlugin(base.Plugin):
	"""
	Plugin for tuning CPU options. Powersaving, governor, required latency, etc.
	"""

	@classmethod
	def tunable_devices(self):
		files = os.listdir("/sys/devices/system/cpu")
		cpus = fnmatch.filter(files, "cpu[0-9]*")
		return map(lambda name: name[3:], cpus)

	def _post_init(self):
		self._latency = None
		self._load_monitor = None
		self._cpu_latency_fd = os.open("/dev/cpu_dma_latency", os.O_WRONLY)

		if self._options["force_latency"] is None:
			self._load_monitor = self._monitors_repository.create("load", None)
		else:
			self._dynamic_tuning = False
			self._set_latency(self._options["force_latency"])

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
			self._monitors_repository.delete(self._load_monitor)

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

	@command_set("governor", per_device=True)
	def _set_governor(self, governor, device):
		log.info("setting governor '%s' on cpu '%s'" % (governor, device))
		tuned.utils.commands.execute(["cpupower", "-c", device, "frequency-set", "-g", governor])

	@command_get("governor")
	def _get_governor(self, device):
		governor = None
		try:
			lines = tuned.utils.commands.execute(["cpupower", "-c", device, "frequency-info", "-p"]).splitlines()
			for line in lines:
				if line.startswith("analyzing"):
					continue
				(drop, drop, governor) = line.split()
				break
		except:
			log.error("could not get current governor on cpu '%s'" % device)
			governor = None

		return governor

	@command_set("multicore_powersave")
	def _set_multicore_powersave(self, value):
		value = int(value)
		if value not in [0, 1, 2]:
			log.error("invalid value of 'multicore_powersave' option")
			return

		log.info("setting CPU multicore scheduler to '%d'" % value)
		tuned.utils.commands.execute(["cpupower", "set", "-m", str(value)])

	@command_get("multicore_powersave")
	def _get_multicore_powersave(self):
		scheduler = None
		try:
			line = tuned.utils.commands.execute(["cpupower", "info", "-m"])
			if line.find("not supported") != -1:
				log.info("'multicore_powersave' is not supported by this system")
			elif line.startswith("System's multi core scheduler setting"):
				(drop, scheduler) = line.split(": ")
		except:
			log.error("could not get current 'multicore_powersave' value")
			scheduler = None

		return scheduler
