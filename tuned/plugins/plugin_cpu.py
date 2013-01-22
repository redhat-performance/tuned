import base
from decorators import *
import tuned.logs
import tuned.utils.commands

import os
import struct

log = tuned.logs.get()

# TODO: force_latency -> command

class CPULatencyPlugin(base.Plugin):
	"""
	Plugin for tuning CPU options. Powersaving, governor, required latency, etc.
	"""

	def _init_devices(self):
		self._devices = set()
		# current list of devices
		for device in self._hardware_inventory.get_devices("cpu"):
			self._devices.add(device.sys_name)

		self._assigned_devices = set()
		self._free_devices = self._devices.copy()

	def _get_config_options(self):
		return {
			"load_threshold"      : 0.2,
			"latency_low"         : 100,
			"latency_high"        : 1000,
			"force_latency"       : None,
			"governor"            : None,
			"multicore_powersave" : None,
		}

	def _instance_init(self, instance):
		instance._has_static_tuning = True
		instance._has_dynamic_tuning = False

		# only the first instance of the plugin can control the latency
		if self._instances.values()[0] == instance:
			instance._controls_latency = True
			self._cpu_latency_fd = os.open("/dev/cpu_dma_latency", os.O_WRONLY)
			self._latency = None

			if instance.options["force_latency"] is None:
				instance._load_monitor = self._monitors_repository.create("load", None)
				instance._has_dynamic_tuning = True
			else:
				instance._load_monitor = None

		else:
			instance._controls_latency = False
			log.info("Latency settings from non-first CPU plugin instance '%s' will be ignored." % instance.name)

	def _instance_cleanup(self, instance):
		if instance._controls_latency:
			os.close(self._cpu_latency_fd)
			if instance._load_monitor is not None:
				self._monitors_repository.delete(instance._load_monitor)

	def _instance_apply_static(self, instance):
		super(self.__class__, self)._instance_apply_static(instance)

		if not instance._controls_latency:
			return

		force_latency_value = instance.options["force_latency"]
		if force_latency_value is not None:
			self._set_latency(force_latency_value)

	def _instance_apply_dynamic(self, instance, device):
		assert(instance._controls_latency)
		load = instance._load_monitor.get_load()["system"]
		if load < instance.options["load_threshold"]:
			self._set_latency(instance.options["latency_high"])
		else:
			self._set_latency(instance.options["latency_low"])

	def _instance_unapply_dynamic(self, instance, device):
		pass

	def _set_latency(self, latency):
		latency = int(latency)
		if self._latency != latency:
			log.info("setting new cpu latency %d" % latency)
			latency_bin = struct.pack("i", latency)
			os.write(self._cpu_latency_fd, latency_bin)
			self._latency = latency

	@command_set("governor", per_device=True)
	def _set_governor(self, governor, device):
		log.info("setting governor '%s' on cpu '%s'" % (governor, device))
		cpu_id = device.lstrip("cpu")
		tuned.utils.commands.execute(["cpupower", "-c", cpu_id, "frequency-set", "-g", str(governor)])

	@command_get("governor")
	def _get_governor(self, device):
		governor = None
		try:
			cpu_id = device.lstrip("cpu")
			lines = tuned.utils.commands.execute(["cpupower", "-c", cpu_id, "frequency-info", "-p"]).splitlines()
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
