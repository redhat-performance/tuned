from tuned.plugins import base
from tuned.plugins.decorators import *
import tuned.logs
from tuned.utils.commands import commands
from tuned.utils.file import FileHandler
import tuned.consts as consts
from .library import CPULatencyLibrary

import os
import struct
import errno
import platform
import procfs

log = tuned.logs.get()

cpuidle_states_path = "/sys/devices/system/cpu/cpu0/cpuidle"

class CPULatencyPlugin(base.Plugin):
	"""
	Plugin for tuning CPU options. Powersaving, governor, required latency, etc.
	"""

	def __init__(self, *args, **kwargs):
		super(CPULatencyPlugin, self).__init__(*args, **kwargs)

		self._has_pm_qos = True
		self._arch = "x86_64"
		self._is_x86 = False
		self._is_intel = False
		self._is_amd = False
		self._has_energy_perf_bias = False
		self._has_intel_pstate = False

		self._min_perf_pct_save = None
		self._max_perf_pct_save = None
		self._no_turbo_save = None
		self._governors_map = {}
		self._cmd = commands()
		file_handler = FileHandler(log_func=log.debug)
		self._lib = CPULatencyLibrary(file_handler, log)

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

	def _check_arch(self):
		intel_archs = [ "x86_64", "i686", "i585", "i486", "i386" ]
		self._arch = platform.machine()

		if self._arch in intel_archs:
                        # Possible other x86 vendors (from arch/x86/kernel/cpu/*):
                        # "CentaurHauls", "CyrixInstead", "Geode by NSC", "HygonGenuine", "GenuineTMx86",
                        # "TransmetaCPU", "UMC UMC UMC"
			cpu = procfs.cpuinfo()
			vendor = cpu.tags.get("vendor_id")
			if vendor == "GenuineIntel":
			        self._is_intel = True
			elif vendor == "AuthenticAMD" or vendor == "HygonGenuine":
			        self._is_amd = True
			else:
				# We always assign Intel, unless we know better
				self._is_intel = True
			log.info("We are running on an x86 %s platform" % vendor)
		else:
			log.info("We are running on %s (non x86)" % self._arch)

		if self._is_intel is True:
			# Check for x86_energy_perf_policy, ignore if not available / supported
			self._check_energy_perf_bias()
			# Check for intel_pstate
			self._check_intel_pstate()

	def _check_energy_perf_bias(self):
		self._has_energy_perf_bias = False
		retcode_unsupported = 1
		retcode, out = self._cmd.execute(["x86_energy_perf_policy", "-r"], no_errors = [errno.ENOENT, retcode_unsupported])
		# With recent versions of the tool, a zero exit code is
		# returned even if EPB is not supported. The output is empty
		# in that case, however.
		if retcode == 0 and out != "":
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

			self._check_arch()
		else:
			instance._first_instance = False
			log.info("Latency settings from non-first CPU plugin instance '%s' will be ignored." % instance.name)

		try:
			instance._first_device = list(instance.assigned_devices)[0]
		except IndexError:
			instance._first_device = None

	def _instance_cleanup(self, instance):
		if instance._first_instance:
			if self._has_pm_qos:
				os.close(self._cpu_latency_fd)
			if instance._load_monitor is not None:
				self._monitors_repository.delete(instance._load_monitor)

	def _getset_intel_pstate_attr(self, attr, value):
		if value is None:
			return None
		v = self._lib.get_intel_pstate_attr(attr)
		self._lib.set_intel_pstate_attr(attr, value)
		return v

	def _instance_apply_static(self, instance):
		super(CPULatencyPlugin, self)._instance_apply_static(instance)

		if not instance._first_instance:
			return

		force_latency_value = self._variables.expand(
			instance.options["force_latency"])
		if force_latency_value is not None:
			self._set_latency(force_latency_value)
		if self._has_intel_pstate:
			new_value = self._variables.expand(
				instance.options["min_perf_pct"])
			self._min_perf_pct_save = self._getset_intel_pstate_attr(
				"min_perf_pct", new_value)
			new_value = self._variables.expand(
				instance.options["max_perf_pct"])
			self._max_perf_pct_save = self._getset_intel_pstate_attr(
				"max_perf_pct", new_value)
			new_value = self._variables.expand(
				instance.options["no_turbo"])
			self._no_turbo_save = self._getset_intel_pstate_attr(
				"no_turbo", new_value)

	def _instance_unapply_static(self, instance, full_rollback = False):
		super(CPULatencyPlugin, self)._instance_unapply_static(instance, full_rollback)

		if instance._first_instance and self._has_intel_pstate:
			self._lib.set_intel_pstate_attr("min_perf_pct", self._min_perf_pct_save)
			self._lib.set_intel_pstate_attr("max_perf_pct", self._max_perf_pct_save)
			self._lib.set_intel_pstate_attr("no_turbo", self._no_turbo_save)

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

	def _str2int(self, s):
		try:
			return int(s)
		except (ValueError, TypeError):
			return None

	def _read_cstates_latency(self):
		self.cstates_latency = {}
		for d in os.listdir(cpuidle_states_path):
			cstate_path = cpuidle_states_path + "/%s/" % d
			name = self._cmd.read_file(cstate_path + "name", err_ret = None, no_error = True)
			latency = self._cmd.read_file(cstate_path + "latency", err_ret = None, no_error = True)
			if name is not None and latency is not None:
				latency = self._str2int(latency)
				if latency is not None:
					self.cstates_latency[name.strip()] = latency

	def _get_latency_by_cstate_name(self, name):
		log.debug("getting latency for cstate with name '%s'" % name)
		if self.cstates_latency is None:
			log.debug("reading cstates latency table")
			self._read_cstates_latency()
		latency = self.cstates_latency.get(name, None)
		log.debug("cstate name mapped to latency: %s" % str(latency))
		return latency

	def _get_latency_by_cstate_id(self, lid):
		log.debug("getting latency for cstate with ID '%s'" % str(lid))
		lid = self._str2int(lid)
		if lid is None:
			log.debug("cstate ID is invalid")
			return None
		latency_path = cpuidle_states_path + "/%s/latency" % ("state%d" % lid)
		latency = self._str2int(self._cmd.read_file(latency_path, err_ret = None, no_error = True))
		log.debug("cstate ID mapped to latency: %s" % str(latency))
		return latency

	# returns (latency, skip), skip means we want to skip latency settings
	def _parse_latency(self, latency):
		self.cstates_latency = None
		latencies = str(latency).split("|")
		log.debug("parsing latency")
		for latency in latencies:
			try:
				latency = int(latency)
				log.debug("parsed directly specified latency value: %d" % latency)
			except ValueError:
				if latency[0:10] == "cstate.id:":
					latency = self._get_latency_by_cstate_id(latency[10:])
				elif latency[0:12] == "cstate.name:":
					latency = self._get_latency_by_cstate_name(latency[12:])
				elif latency in ["none", "None"]:
					log.debug("latency 'none' specified")
					return None, True
				else:
					latency = None
					log.debug("invalid latency specified: '%s'" % str(latency))
			if latency is not None:
				break
		return latency, False

	def _set_latency(self, latency):
		latency, skip = self._parse_latency(latency)
		if not skip and self._has_pm_qos:
			if latency is None:
				log.error("unable to evaluate latency value (probably wrong settings in the 'cpu' section of current profile), disabling PM QoS")
				self._has_pm_qos = False
			elif self._latency != latency:
				log.info("setting new cpu latency %d" % latency)
				latency_bin = struct.pack("i", latency)
				os.write(self._cpu_latency_fd, latency_bin)
				self._latency = latency

	@command_set("governor", per_device=True)
	def _set_governor(self, governors, device, sim):
		if not self._check_cpu_can_change_governor(device):
			return None
		governors = str(governors)
		governors = governors.split("|")
		governors = [governor.strip() for governor in governors]
		for governor in governors:
			if len(governor) == 0:
				log.error("The 'governor' option contains an empty value.")
				return None
		available_governors = self._lib.get_available_governors(device)
		for governor in governors:
			if governor in available_governors:
				if not sim:
					self._lib.set_governor_on_cpu(governor, device)
				break
			elif not sim:
				log.debug("Ignoring governor '%s' on cpu '%s', it is not supported"
						% (governor, device))
		else:
			log.warn("None of the scaling governors is supported: %s"
					% ", ".join(governors))
			governor = None
		return governor

	@command_get("governor")
	def _get_governor(self, device, ignore_missing=False):
		governor = None
		if not self._check_cpu_can_change_governor(device):
			return None
		data = self._lib.get_governor_on_cpu(device, ignore_missing)
		if len(data) > 0:
			governor = data

		if governor is None:
			log.error("could not get current governor on cpu '%s'" % device)

		return governor

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
			path = self._lib.sampling_down_factor_path(governor)
			if not os.path.exists(path):
				log.debug("ignoring sampling_down_factor setting for CPU '%s', governor '%s' doesn't support it" % (device, governor))
				return None
			val = str(sampling_down_factor)
			if not sim:
				self._lib.set_sampling_down_factor(path, val, governor)
		return val

	@command_get("sampling_down_factor")
	def _get_sampling_down_factor(self, device, ignore_missing=False):
		governor = self._get_governor(device, ignore_missing=ignore_missing)
		if governor is None:
			return None
		path = self._lib.sampling_down_factor_path(governor)
		if not os.path.exists(path):
			return None
		return self._lib.get_sampling_down_factor(path, governor)

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
