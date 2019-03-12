from . import base
from .decorators import *
import tuned.logs
from tuned.utils.nettool import ethcard
from tuned.utils.commands import commands
import os
import re

log = tuned.logs.get()

WOL_VALUES = "pumbagsd"

class NetTuningPlugin(base.Plugin):
	"""
	Plugin for ethernet card options tuning.
	"""

	def __init__(self, *args, **kwargs):
		super(NetTuningPlugin, self).__init__(*args, **kwargs)
		self._load_smallest = 0.05
		self._level_steps = 6
		self._cmd = commands()

	def _init_devices(self):
		self._devices_supported = True
		self._free_devices = set()
		self._assigned_devices = set()

		re_not_virtual = re.compile('(?!.*/virtual/.*)')
		for device in self._hardware_inventory.get_devices("net"):
			if re_not_virtual.match(device.device_path):
				self._free_devices.add(device.sys_name)

		log.debug("devices: %s" % str(self._free_devices));

	def _get_device_objects(self, devices):
		return [self._hardware_inventory.get_device("net", x) for x in devices]

	def _instance_init(self, instance):
		instance._has_static_tuning = True
		if self._option_bool(instance.options["dynamic"]):
			instance._has_dynamic_tuning = True
			instance._load_monitor = self._monitors_repository.create("net", instance.assigned_devices)
			instance._idle = {}
			instance._stats = {}
		else:
			instance._has_dynamic_tuning = False
			instance._load_monitor = None
			instance._idle = None
			instance._stats = None

	def _instance_cleanup(self, instance):
		if instance._load_monitor is not None:
			self._monitors_repository.delete(instance._load_monitor)
			instance._load_monitor = None

	def _instance_apply_dynamic(self, instance, device):
		self._instance_update_dynamic(instance, device)

	def _instance_update_dynamic(self, instance, device):
		load = [int(value) for value in instance._load_monitor.get_device_load(device)]
		if load is None:
			return

		if not device in instance._stats:
			self._init_stats_and_idle(instance, device)
		self._update_stats(instance, device, load)
		self._update_idle(instance, device)

		stats = instance._stats[device]
		idle = instance._idle[device]

		if idle["level"] == 0 and idle["read"] >= self._level_steps and idle["write"] >= self._level_steps:
			idle["level"] = 1
			log.info("%s: setting 100Mbps" % device)
			ethcard(device).set_speed(100)
		elif idle["level"] == 1 and (idle["read"] == 0 or idle["write"] == 0):
			idle["level"] = 0
			log.info("%s: setting max speed" % device)
			ethcard(device).set_max_speed()

		log.debug("%s load: read %0.2f, write %0.2f" % (device, stats["read"], stats["write"]))
		log.debug("%s idle: read %d, write %d, level %d" % (device, idle["read"], idle["write"], idle["level"]))

	@classmethod
	def _get_config_options_coalesce(cls):
		return {
			"adaptive-rx": None,
			"adaptive-tx": None,
			"rx-usecs": None,
			"rx-frames": None,
			"rx-usecs-irq": None,
			"rx-frames-irq": None,
			"tx-usecs": None,
			"tx-frames": None,
			"tx-usecs-irq": None,
			"tx-frames-irq": None,
			"stats-block-usecs": None,
			"pkt-rate-low": None,
			"rx-usecs-low": None,
			"rx-frames-low": None,
			"tx-usecs-low": None,
			"tx-frames-low": None,
			"pkt-rate-high": None,
			"rx-usecs-high": None,
			"rx-frames-high": None,
			"tx-usecs-high": None,
			"tx-frames-high": None,
			"sample-interval": None
			}

	@classmethod
	def _get_config_options_pause(cls):
		return { "autoneg": None,
			"rx": None,
			"tx": None }

	@classmethod
	def _get_config_options_ring(cls):
		return { "rx": None,
			"rx-mini": None,
			"rx-jumbo": None,
			"tx": None }

	@classmethod
	def _get_config_options(cls):
		return {
			"dynamic": True,
			"wake_on_lan": None,
			"nf_conntrack_hashsize": None,
			"features": None,
			"coalesce": None,
			"pause": None,
			"ring": None,
		}

	def _init_stats_and_idle(self, instance, device):
		max_speed = self._calc_speed(ethcard(device).get_max_speed())
		instance._stats[device] = { "new": 4 * [0], "max": 2 * [max_speed, 1] }
		instance._idle[device] = { "level": 0, "read": 0, "write": 0 }

	def _update_stats(self, instance, device, new_load):
		# put new to old
		instance._stats[device]["old"] = old_load = instance._stats[device]["new"]
		instance._stats[device]["new"] = new_load

		# load difference
		diff = [new_old[0] - new_old[1] for new_old in zip(new_load, old_load)]
		instance._stats[device]["diff"] = diff

		# adapt maximum expected load if the difference is higer
		old_max_load = instance._stats[device]["max"]
		max_load = [max(pair) for pair in zip(old_max_load, diff)]
		instance._stats[device]["max"] = max_load

		# read/write ratio
		instance._stats[device]["read"] =  float(diff[0]) / float(max_load[0])
		instance._stats[device]["write"] = float(diff[2]) / float(max_load[2])

	def _update_idle(self, instance, device):
		# increase counter if there is no load, otherwise reset the counter
		for operation in ["read", "write"]:
			if instance._stats[device][operation] < self._load_smallest:
				instance._idle[device][operation] += 1
			else:
				instance._idle[device][operation] = 0

	def _instance_unapply_dynamic(self, instance, device):
		if device in instance._idle and instance._idle[device]["level"] > 0:
			instance._idle[device]["level"] = 0
			log.info("%s: setting max speed" % device)
			ethcard(device).set_max_speed()

	def _calc_speed(self, speed):
		# 0.6 is just a magical constant (empirical value): Typical workload on netcard won't exceed
		# that and if it does, then the code is smart enough to adapt it.
		# 1024 * 1024 as for MB -> B
		# speed / 7  Mb -> MB
		return (int) (0.6 * 1024 * 1024 * speed / 8)

	# parse features/coalesce config parameters (those defined in profile configuration)
	# context is for error message
	def _parse_config_parameters(self, value, context):
		# split supporting various dellimeters
		v = str(re.sub(r"(:\s*)|(\s+)|(\s*;\s*)|(\s*,\s*)", " ", value)).split()
		lv = len(v)
		if lv % 2 != 0:
			log.error("invalid %s parameter: '%s'" % (context, str(value)))
			return None
		if lv == 0:
			return dict()
		# convert flat list to dict
		return dict(list(zip(v[::2], v[1::2])))

	# parse features/coalesce device parameters (those returned by ethtool)
	def _parse_device_parameters(self, value):
		# substitute "Adaptive RX: val1  TX: val2" to 'adaptive-rx: val1' and
		# 'adaptive-tx: val2' and workaround for ethtool inconsistencies
		# (rhbz#1225375)
		value = self._cmd.multiple_re_replace({
			"Adaptive RX:": "adaptive-rx:",
			"\s+TX:": "\nadaptive-tx:",
			"rx-frame-low:": "rx-frames-low:",
			"rx-frame-high:": "rx-frames-high:",
			"tx-frame-low:": "tx-frames-low:",
			"tx-frame-high:": "tx-frames-high:",
			"large-receive-offload:": "lro:",
			"rx-checksumming:": "rx:",
			"tx-checksumming:": "tx:",
			"scatter-gather:": "sg:",
			"tcp-segmentation-offload:": "tso:",
			"udp-fragmentation-offload:": "ufo:",
			"generic-segmentation-offload:": "gso:",
			"generic-receive-offload:": "gro:",
			"rx-vlan-offload:": "rxvlan:",
			"tx-vlan-offload:": "txvlan:",
			"ntuple-filters:": "ntuple:",
			"receive-hashing:": "rxhash:",
		}, value)
		# remove empty lines, remove fixed parameters (those with "[fixed]")
		vl = [v for v in value.split('\n') if len(str(v)) > 0 and not re.search("\[fixed\]$", str(v))]
		if len(vl) < 2:
			return None
		# skip first line (device name), split to key/value,
		# remove pairs which are not key/value
		return dict([u for u in [re.split(r":\s*", str(v)) for v in vl[1:]] if len(u) == 2])

	@classmethod
	def _nf_conntrack_hashsize_path(self):
		return "/sys/module/nf_conntrack/parameters/hashsize"

	@command_set("wake_on_lan", per_device=True)
	def _set_wake_on_lan(self, value, device, sim):
		if value is None:
			return None

		# see man ethtool for possible wol values, 0 added as an alias for 'd'
		value = re.sub(r"0", "d", str(value));
		if not re.match(r"^[" + WOL_VALUES + r"]+$", value):
			log.warn("Incorrect 'wake_on_lan' value.")
			return None

		if not sim:
			self._cmd.execute(["ethtool", "-s", device, "wol", value])
		return value

	@command_get("wake_on_lan")
	def _get_wake_on_lan(self, device, ignore_missing=False):
		value = None
		try:
			m = re.match(r".*Wake-on:\s*([" + WOL_VALUES + "]+).*", self._cmd.execute(["ethtool", device])[1], re.S)
			if m:
				value = m.group(1)
		except IOError:
			pass
		return value

	@command_set("nf_conntrack_hashsize")
	def _set_nf_conntrack_hashsize(self, value, sim):
		if value is None:
			return None

		hashsize = int(value)
		if hashsize >= 0:
			if not sim:
				self._cmd.write_to_file(self._nf_conntrack_hashsize_path(), hashsize)
			return hashsize
		else:
			return None

	@command_get("nf_conntrack_hashsize")
	def _get_nf_conntrack_hashsize(self):
		value = self._cmd.read_file(self._nf_conntrack_hashsize_path())
		if len(value) > 0:
			return int(value)
		return None

	# d is dict: {parameter: value}
	def _check_parameters(self, context, d):
		if context == "features":
			return True
		params = set(d.keys())
		supported_getter = { "coalesce": self._get_config_options_coalesce, \
				"pause": self._get_config_options_pause, \
				"ring": self._get_config_options_ring }
		supported = set(supported_getter[context]().keys())
		if not params.issubset(supported):
			log.error("unknown %s parameter(s): %s" % (context, str(params - supported)))
			return False
		return True

	# parse output of ethtool -a
	def _parse_pause_parameters(self, s):
		s = self._cmd.multiple_re_replace(\
				{"Autonegotiate": "autoneg",
				"RX": "rx",
				"TX": "tx"}, s)
		l = s.split("\n")[1:]
		l = [x for x in l if x != '' and not re.search(r"\[fixed\]", x)]
		return dict([x for x in [re.split(r":\s*", x) for x in l] if len(x) == 2])

	# parse output of ethtool -g
	def _parse_ring_parameters(self, s):
		a = re.split(r"^Current hardware settings:$", s, flags=re.MULTILINE)
		s = a[1]
		s = self._cmd.multiple_re_replace(\
				{"RX": "rx",
				"RX Mini": "rx-mini",
				"RX Jumbo": "rx-jumbo",
				"TX": "tx"}, s)
		l = s.split("\n")
		l = [x for x in l if x != '']
		l = [x for x in [re.split(r":\s*", x) for x in l] if len(x) == 2]
		return dict(l)

	def _check_device_support(self, context, parameters, device, dev_params):
		"""Filter unsupported parameters and log warnings about it

		Positional parameters:
		context -- context of change
		parameters -- parameters to change
		device -- name of device on which should be parameters set
		dev_params -- dictionary of currently known parameters of device
		"""
		supported_parameters = set(dev_params.keys())
		parameters_to_change = set(parameters.keys())
		# if parameters_to_change contains unsupported parameter(s) then remove
		# it/them
		unsupported_parameters = (parameters_to_change
			- supported_parameters)
		for param in unsupported_parameters:
			log.warning("%s parameter %s is not supported by device %s" % (
				context,
				param,
				device,
			))
			parameters.pop(param, None)

	def _get_device_parameters(self, context, device):
		context2opt = { "coalesce": "-c", "features": "-k", "pause": "-a", "ring": "-g" }
		opt = context2opt[context]
		ret, value = self._cmd.execute(["ethtool", opt, device])
		if ret != 0 or len(value) == 0:
			return None
		context2parser = { "coalesce": self._parse_device_parameters, \
				"features": self._parse_device_parameters, \
				"pause": self._parse_pause_parameters, \
				"ring": self._parse_ring_parameters }
		parser = context2parser[context]
		d = parser(value)
		if context == "coalesce" and not self._check_parameters(context, d):
			return None
		return d

	def _set_device_parameters(self, context, value, device, sim,
				dev_params = None):
		if value is None or len(value) == 0:
			return None
		d = self._parse_config_parameters(value, context)
		if d is None or not self._check_parameters(context, d):
			return {}
		# check if device supports parameters and filter out unsupported ones
		if dev_params:
			self._check_device_support(context, d, device, dev_params)

		if not sim and len(d) != 0:
			log.debug("setting %s: %s" % (context, str(d)))
			context2opt = { "coalesce": "-C", "features": "-K", "pause": "-A", "ring": "-G" }
			opt = context2opt[context]
			# ignore ethtool return code 80, it means parameter is already set
			self._cmd.execute(["ethtool", opt, device] + self._cmd.dict2list(d), no_errors = [80])
		return d

	def _custom_parameters(self, context, start, value, device, verify):
		storage_key = self._storage_key(
				command_name = context,
				device_name = device)
		if start:
			params_current = self._get_device_parameters(context,
					device)
			params_set = self._set_device_parameters(context,
					value, device, verify,
					dev_params = params_current)
			# if none of parameters passed checks then the command completely
			# failed
			if len(params_set) == 0:
				return False
			relevant_params_current = [(param, value) for param, value
					in params_current.items()
					if param in params_set]
			relevant_params_current = dict(relevant_params_current)
			if verify:
				res = (self._cmd.dict2list(params_set)
						== self._cmd.dict2list(relevant_params_current))
				self._log_verification_result(context, res,
						params_set,
						relevant_params_current,
						device = device)
				return res
			# saved are only those parameters which passed checks
			self._storage.set(storage_key, " ".join(
					self._cmd.dict2list(relevant_params_current)))
		else:
			original_value = self._storage.get(storage_key)
			# in storage are only those parameters which were already tested
			# so skip check for supported parameters
			self._set_device_parameters(context, original_value, device, False)
		return None

	@command_custom("features", per_device = True)
	def _features(self, start, value, device, verify, ignore_missing):
		return self._custom_parameters("features", start, value, device, verify)

	@command_custom("coalesce", per_device = True)
	def _coalesce(self, start, value, device, verify, ignore_missing):
		return self._custom_parameters("coalesce", start, value, device, verify)

	@command_custom("pause", per_device = True)
	def _pause(self, start, value, device, verify, ignore_missing):
		return self._custom_parameters("pause", start, value, device, verify)

	@command_custom("ring", per_device = True)
	def _ring(self, start, value, device, verify, ignore_missing):
		return self._custom_parameters("ring", start, value, device, verify)
