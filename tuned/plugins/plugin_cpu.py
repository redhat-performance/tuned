from . import base
from .decorators import *
import tuned.logs
from tuned.utils.commands import commands
import tuned.consts as consts

import os
import struct
import errno

log = tuned.logs.get()

# TODO: force_latency -> command
#       intel_pstate

class CPULatencyPlugin(base.Plugin):
	"""
	Plugin for tuning CPU options. Powersaving, governor, required latency, etc.
	"""

	def __init__(self, *args, **kwargs):
		super(CPULatencyPlugin, self).__init__(*args, **kwargs)

		self._has_pm_qos = True
		self._has_energy_perf_bias = True
		self._has_intel_pstate = False

		self._min_perf_pct_save = None
		self._max_perf_pct_save = None
		self._no_turbo_save = None
		self._governors_map = {}
		self._cmd = commands()

	def _init_devices(self):
		self._devices_supported = True
		self._free_devices = set()
		# current list of devices
		for device in self._hardware_inventory.get_devices("cpu"):
			self._free_devices.add(device.sys_name)

		self._assigned_devices = set()

	def _get_device_objects(self, devices):
		return [self._hardware_inventory.get_device("cpu", x) for x in devices]

	@classmethod
	def _get_config_options(self):
		return {
			"load_threshold"       : 0.2,
			"latency_low"          : 100,
			"latency_high"         : 1000,
			"force_latency"        : None,
			"governor"             : None,
			"sampling_down_factor" : None,
			"energy_perf_bias"     : None,
			"min_perf_pct"         : None,
			"max_perf_pct"         : None,
			"no_turbo"             : None,
		}

	def _check_energy_perf_bias(self):
		self._has_energy_perf_bias = False
		retcode_unsupported = 1
		retcode = self._cmd.execute(["x86_energy_perf_policy", "-r"], no_errors = [errno.ENOENT, retcode_unsupported])[0]
		if retcode == 0:
			self._has_energy_perf_bias = True
		elif retcode < 0:
			log.warning("unable to run x86_energy_perf_policy tool, ignoring CPU energy performance bias, is the tool installed?")
		else:
			log.warning("your CPU doesn't support MSR_IA32_ENERGY_PERF_BIAS, ignoring CPU energy performance bias")

	def _check_intel_pstate(self):
		self._has_intel_pstate = os.path.exists("/sys/devices/system/cpu/intel_pstate")
		if self._has_intel_pstate:
			log.info("intel_pstate detected")

	def _is_cpu_online(self, device):
		sd = str(device)
		return self._cmd.is_cpu_online(str(device).replace("cpu", ""))

	def _cpu_has_scaling_governor(self, device):
		return os.path.exists("/sys/devices/system/cpu/%s/cpufreq/scaling_governor" % device)

	def _check_cpu_can_change_governor(self, device):
		if not self._is_cpu_online(device):
			log.debug("'%s' is not online, skipping" % device)
			return False
		if not self._cpu_has_scaling_governor(device):
			log.debug("there is no scaling governor fo '%s', skipping" % device)
			return False
		return True

	def _instance_init(self, instance):
		instance._has_static_tuning = True
		instance._has_dynamic_tuning = False

		# only the first instance of the plugin can control the latency
		if list(self._instances.values())[0] == instance:
			instance._first_instance = True
			try:
				self._cpu_latency_fd = os.open(consts.PATH_CPU_DMA_LATENCY, os.O_WRONLY)
			except OSError:
				log.error("Unable to open '%s', disabling PM_QoS control" % consts.PATH_CPU_DMA_LATENCY)
				self._has_pm_qos = False
			self._latency = None

			if instance.options["force_latency"] is None:
				instance._load_monitor = self._monitors_repository.create("load", None)
				instance._has_dynamic_tuning = True
			else:
				instance._load_monitor = None

			# Check for x86_energy_perf_policy, ignore if not available / supported
			self._check_energy_perf_bias()
			# Check for intel_pstate
			self._check_intel_pstate()
		else:
			instance._first_instance = False
			log.info("Latency settings from non-first CPU plugin instance '%s' will be ignored." % instance.name)

		instance._first_device = list(instance.devices)[0]

	def _instance_cleanup(self, instance):
		if instance._first_instance:
			if self._has_pm_qos:
				os.close(self._cpu_latency_fd)
			if instance._load_monitor is not None:
				self._monitors_repository.delete(instance._load_monitor)

	def _get_intel_pstate_attr(self, attr):
		return self._cmd.read_file("/sys/devices/system/cpu/intel_pstate/%s" % attr, None).strip()

	def _set_intel_pstate_attr(self, attr, val):
		if val is not None:
			self._cmd.write_to_file("/sys/devices/system/cpu/intel_pstate/%s" % attr, val)

	def _getset_intel_pstate_attr(self, attr, value):
		if value is None:
			return None
		v = self._get_intel_pstate_attr(attr)
		self._set_intel_pstate_attr(attr, value)
		return v

	def _instance_apply_static(self, instance):
		super(CPULatencyPlugin, self)._instance_apply_static(instance)

		if not instance._first_instance:
			return

		force_latency_value = instance.options["force_latency"]
		if force_latency_value is not None:
			self._set_latency(force_latency_value)
		if self._has_intel_pstate:
			self._min_perf_pct_save = self._getset_intel_pstate_attr("min_perf_pct", instance.options["min_perf_pct"])
			self._max_perf_pct_save = self._getset_intel_pstate_attr("max_perf_pct", instance.options["max_perf_pct"])
			self._no_turbo_save = self._getset_intel_pstate_attr("no_turbo", instance.options["no_turbo"])

	def _instance_unapply_static(self, instance, full_rollback = False):
		super(CPULatencyPlugin, self)._instance_unapply_static(instance, full_rollback)

		if instance._first_instance and self._has_intel_pstate:
			self._set_intel_pstate_attr("min_perf_pct", self._min_perf_pct_save)
			self._set_intel_pstate_attr("max_perf_pct", self._max_perf_pct_save)
			self._set_intel_pstate_attr("no_turbo", self._no_turbo_save)

	def _instance_apply_dynamic(self, instance, device):
		self._instance_update_dynamic(instance, device)

	def _instance_update_dynamic(self, instance, device):
		assert(instance._first_instance)
		if device != instance._first_device:
			return

		load = instance._load_monitor.get_load()["system"]
		if load < instance.options["load_threshold"]:
			self._set_latency(instance.options["latency_high"])
		else:
			self._set_latency(instance.options["latency_low"])

	def _instance_unapply_dynamic(self, instance, device):
		pass

	def _set_latency(self, latency):
		latency = int(latency)
		if self._has_pm_qos and self._latency != latency:
			log.info("setting new cpu latency %d" % latency)
			latency_bin = struct.pack("i", latency)
			os.write(self._cpu_latency_fd, latency_bin)
			self._latency = latency

	def _get_available_governors(self, device):
		return self._cmd.read_file("/sys/devices/system/cpu/%s/cpufreq/scaling_available_governors" % device).strip().split()

	@command_set("governor", per_device=True)
	def _set_governor(self, governor, device, sim):
		if not self._check_cpu_can_change_governor(device):
			return None
		if governor not in self._get_available_governors(device):
			if not sim:
				log.info("ignoring governor '%s' on cpu '%s', it is not supported" % (governor, device))
			return None
		if not sim:
			log.info("setting governor '%s' on cpu '%s'" % (governor, device))
			self._cmd.write_to_file("/sys/devices/system/cpu/%s/cpufreq/scaling_governor" % device, str(governor))
		return str(governor)

	@command_get("governor")
	def _get_governor(self, device, ignore_missing=False):
		governor = None
		if not self._check_cpu_can_change_governor(device):
			return None
		data = self._cmd.read_file("/sys/devices/system/cpu/%s/cpufreq/scaling_governor" % device, no_error=ignore_missing).strip()
		if len(data) > 0:
			governor = data

		if governor is None:
			log.error("could not get current governor on cpu '%s'" % device)

		return governor

	def _sampling_down_factor_path(self, governor = "ondemand"):
		return "/sys/devices/system/cpu/cpufreq/%s/sampling_down_factor" % governor

	@command_set("sampling_down_factor", per_device = True, priority = 10)
	def _set_sampling_down_factor(self, sampling_down_factor, device, sim):
		val = None

		# hack to clear governors map when the profile starts unloading
		# TODO: this should be handled better way, by e.g. currently non-implemented
		# Plugin.profile_load_finished() method
		if device in self._governors_map:
			self._governors_map.clear()

		self._governors_map[device] = None
		governor = self._get_governor(device)
		if governor is None:
			log.debug("ignoring sampling_down_factor setting for CPU '%s', cannot match governor" % device)
			return None
		if governor not in list(self._governors_map.values()):
			self._governors_map[device] = governor
			path = self._sampling_down_factor_path(governor)
			if not os.path.exists(path):
				log.debug("ignoring sampling_down_factor setting for CPU '%s', governor '%s' doesn't support it" % (device, governor))
				return None
			val = str(sampling_down_factor)
			if not sim:
				log.info("setting sampling_down_factor to '%s' for governor '%s'" % (val, governor))
				self._cmd.write_to_file(path, val)
		return val

	@command_get("sampling_down_factor")
	def _get_sampling_down_factor(self, device, ignore_missing=False):
		governor = self._get_governor(device, ignore_missing=ignore_missing)
		if governor is None:
			return None
		path = self._sampling_down_factor_path(governor)
		if not os.path.exists(path):
			return None
		return self._cmd.read_file(path).strip()

	def _try_set_energy_perf_bias(self, cpu_id, value):
		(retcode, out, err_msg) = self._cmd.execute(
				["x86_energy_perf_policy",
				"-c", cpu_id,
				str(value)
				],
				return_err = True)
		return (retcode, err_msg)

	@command_set("energy_perf_bias", per_device=True)
	def _set_energy_perf_bias(self, energy_perf_bias, device, sim):
		if not self._is_cpu_online(device):
			log.debug("%s is not online, skipping" % device)
			return None
		if self._has_energy_perf_bias:
			if not sim:
				cpu_id = device.lstrip("cpu")
				vals = energy_perf_bias.split('|')
				for val in vals:
					val = val.strip()
					log.debug("Trying to set energy_perf_bias to '%s' on cpu '%s'"
							% (val, device))
					(retcode, err_msg) = self._try_set_energy_perf_bias(
							cpu_id, val)
					if retcode == 0:
						log.info("energy_perf_bias successfully set to '%s' on cpu '%s'"
								% (val, device))
						break
					elif retcode < 0:
						log.error("Failed to set energy_perf_bias: %s"
								% err_msg)
						break
					else:
						log.debug("Could not set energy_perf_bias to '%s' on cpu '%s', trying another value"
								% (val, device))
				else:
					log.error("Failed to set energy_perf_bias on cpu '%s'. Is the value in the profile correct?"
							% device)
			return str(energy_perf_bias)
		else:
			return None

	def _try_parse_num(self, s):
		try:
			v = int(s)
		except ValueError as e:
			try:
				v = int(s, 16)
			except ValueError as e:
				v = s
		return v

	# Before Linux 4.13
	def _energy_perf_policy_to_human(self, s):
		return {0:"performance", 6:"normal", 15:"powersave"}.get(self._try_parse_num(s), s)

	# Since Linux 4.13
	def _energy_perf_policy_to_human_v2(self, s):
		return {0:"performance",
				4:"balance-performance",
				6:"normal",
				8:"balance-power",
				15:"power",
				}.get(self._try_parse_num(s), s)

	@command_get("energy_perf_bias")
	def _get_energy_perf_bias(self, device, ignore_missing=False):
		energy_perf_bias = None
		if not self._is_cpu_online(device):
			log.debug("%s is not online, skipping" % device)
			return None
		if self._has_energy_perf_bias:
			cpu_id = device.lstrip("cpu")
			retcode, lines = self._cmd.execute(["x86_energy_perf_policy", "-c", cpu_id, "-r"])
			if retcode == 0:
				for line in lines.splitlines():
					l = line.split()
					if len(l) == 2:
						energy_perf_bias = self._energy_perf_policy_to_human(l[1])
						break
					elif len(l) == 3:
						energy_perf_bias = self._energy_perf_policy_to_human_v2(l[2])
						break

		return energy_perf_bias
