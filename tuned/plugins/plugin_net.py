import errno
from . import hotplug
from .decorators import *
import tuned.logs
from tuned.utils.nettool import ethcard
from tuned.utils.commands import commands
import os
import re

log = tuned.logs.get()

WOL_VALUES = "pumbagsd"

class NetTuningPlugin(hotplug.Plugin):
	"""
	Configures network driver, hardware and Netfilter settings.
	Dynamic change of the interface speed according to the interface
	utilization is also supported. The dynamic tuning is controlled by
	the [option]`dynamic` and the global [option]`dynamic_tuning`
	option in `tuned-main.conf`.

	`wake_on_lan`:::
	The [option]`wake_on_lan` option sets wake-on-lan to the specified
	value as when using the `ethtool` utility.
	+
	.Set Wake-on-LAN for device eth0 on MagicPacket(TM)
	====
	----
	[net]
	devices=eth0
	wake_on_lan=g
	----
	====

	`coalesce`:::
	The [option]`coalesce` option allows changing coalescing settings
	for the specified network devices. The syntax is:
	+
	[subs="+quotes,+macros"]
	----
	coalesce=__param1__ __value1__ __param2__ __value2__ ... __paramN__ __valueN__
	----
	+
	Note that not all the coalescing parameters are supported by all
	network cards. For the list of coalescing parameters of your network
	device, use `ethtool -c device`.
	+
	.Setting coalescing parameters rx/tx-usecs for all network devices
	====
	----
	[net]
	coalesce=rx-usecs 3 tx-usecs 16
	----
	====

	`features`:::
	The [option]`features` option allows changing 
	the offload parameters and other features for the specified
	network devices. To query the features of your network device,
	use `ethtool -k device`. The syntax of the option is the same as
	the [option]`coalesce` option.
	+
	.Turn off TX checksumming, generic segmentation and receive offload 
	====
	----
	[net]
	features=tx off gso off gro off
	----
	====

	`pause`:::
	The [option]`pause` option allows changing the pause parameters for
	the specified network devices. To query the pause parameters of your
	network device, use `ethtool -a device`. The syntax of the option
	is the same as the [option]`coalesce` option.
	+
	.Disable autonegotiation
	====
	----
	[net]
	pause=autoneg off
	----
	====

	`ring`:::
	The [option]`ring` option allows changing the rx/tx ring parameters
	for the specified network devices. To query the ring parameters of your
	network device, use `ethtool -g device`. The syntax of the option
	is the same as the [option]`coalesce` option.
	+
	.Change the number of ring entries for the Rx/Tx rings to 1024/512 respectively
	=====
	-----
	[net]
	ring=rx 1024 tx 512
	-----
	=====

	`channels`:::
	The [option]`channels` option allows changing the numbers of channels
	for the specified network device. A channel is an IRQ and the set
	of queues that can trigger that IRQ. To query the channels parameters of your
	network device, use `ethtool -l device`. The syntax of the option
	is the same as the [option]`coalesce` option.
	+
	.Set the number of multi-purpose channels to 16
	=====
	-----
	[net]
	channels=combined 16
	-----
	=====
	+
	A network device either supports rx/tx or combined queue
	mode. The [option]`channels` option automatically adjusts the
	parameters based on the mode supported by the device as long as a
	valid configuration is requested.

	`nf_conntrack_hashsize`:::
	The [option]`nf_conntrack_hashsize` option sets the size of the hash
	table which stores lists of conntrack entries by writing to
	`/sys/module/nf_conntrack/parameters/hashsize`.
	+
	.Adjust the size of the conntrack hash table
	====
	----
	[net]
	nf_conntrack_hashsize=131072
	----
	====

	`txqueuelen`:::
	The [option]`txqueuelen` option allows changing txqueuelen (the length
	of the transmit queue). It uses `ip` utility that is in package	iproute
	recommended for TuneD, so the package needs to be installed for its correct
	functionality. To query the txqueuelen parameters of your network device
	use `ip link show` and the current value is shown after the qlen column.
	+
	.Adjust the length of the transmit queue
	====
	----
	[net]
	txqueuelen=5000
	----
	====

	`mtu`:::
	The [option]`mtu` option allows changing MTU (Maximum Transmission Unit).
	It uses `ip` utility that is in package	iproute recommended for TuneD, so
	the package needs to be installed for its correct functionality. To query
	the MTU parameters of your network device use `ip link show` and the
	current value is shown after the MTU column.
	+
	.Adjust the size of the MTU
	====
	----
	[net]
	mtu=9000
	----
	====
	"""

	def __init__(self, *args, **kwargs):
		super(NetTuningPlugin, self).__init__(*args, **kwargs)
		self._load_smallest = 0.05
		self._level_steps = 6
		self._cmd = commands()
		self._re_ip_link_show = {}
		self._use_ip = True

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
		instance._load_monitor = None
		instance._idle = None
		instance._stats = None
		instance._has_dynamic_tuning = self._option_bool(instance.options["dynamic"])

	def _instance_cleanup(self, instance):
		if instance._load_monitor is not None:
			self._monitors_repository.delete(instance._load_monitor)
			instance._load_monitor = None

	def _instance_init_dynamic(self, instance):
		super(NetTuningPlugin, self)._instance_init_dynamic(instance)
		instance._idle = {}
		instance._stats = {}
		instance._load_monitor = self._monitors_repository.create("net", instance.assigned_devices)

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
	def _get_config_options_channels(cls):
		return { "rx": None,
			"tx": None,
			"other": None,
			"combined": None }

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
			"channels": None,
			"txqueuelen": None,
			"mtu": None,
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
		# speed / 8  Mb -> MB
		return (int) (0.6 * 1024 * 1024 * speed / 8)

	# parse features/coalesce config parameters (those defined in profile configuration)
	# context is for error message
	def _parse_config_parameters(self, value, context):
		# expand config variables
		value = self._variables.expand(value)
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
			"\\s+TX:": "\nadaptive-tx:",
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
		vl = [v for v in value.split('\n') if len(str(v)) > 0 and not re.search(r"\[fixed\]$", str(v))]
		if len(vl) < 2:
			return None
		# skip first line (device name), split to key/value,
		# remove pairs which are not key/value
		return dict([u for u in [re.split(r":\s*", str(v)) for v in vl[1:]] if len(u) == 2])

	@classmethod
	def _nf_conntrack_hashsize_path(self):
		return "/sys/module/nf_conntrack/parameters/hashsize"

	@command_set("wake_on_lan", per_device=True)
	def _set_wake_on_lan(self, value, device, sim, remove):
		if value is None:
			return None

		# see man ethtool for possible wol values, 0 added as an alias for 'd'
		value = re.sub(r"0", "d", str(value));
		if not re.match(r"^[" + WOL_VALUES + r"]+$", value):
			log.warning("Incorrect 'wake_on_lan' value.")
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
	def _set_nf_conntrack_hashsize(self, value, sim, remove):
		if value is None:
			return None

		hashsize = int(value)
		if hashsize >= 0:
			if not sim:
				self._cmd.write_to_file(self._nf_conntrack_hashsize_path(), hashsize, \
					no_error = [errno.ENOENT] if remove else False)
			return hashsize
		else:
			return None

	@command_get("nf_conntrack_hashsize")
	def _get_nf_conntrack_hashsize(self):
		value = self._cmd.read_file(self._nf_conntrack_hashsize_path())
		if len(value) > 0:
			return int(value)
		return None

	def _call_ip_link(self, args=[]):
		if not self._use_ip:
			return None
		args = ["ip", "link"] + args
		(rc, out, err_msg) = self._cmd.execute(args, no_errors=[errno.ENOENT], return_err=True)
		if rc == -errno.ENOENT:
			log.warning("ip command not found, ignoring for other devices")
			self._use_ip = False
			return None
		elif rc:
			log.info("Problem calling ip command")
			log.debug("(rc: %s, msg: '%s')" % (rc, err_msg))
			return None
		return out

	def _ip_link_show(self, device=None):
		args = ["show"]
		if device:
			args.append(device)
		return self._call_ip_link(args)

	@command_set("txqueuelen", per_device=True)
	def _set_txqueuelen(self, value, device, sim, remove):
		if value is None:
			return None
		try:
			int(value)
		except ValueError:
			log.warning("txqueuelen value '%s' is not integer" % value)
			return None
		if not sim:
			# there is inconsistency in "ip", where "txqueuelen" is set as it, but is shown as "qlen"
			res = self._call_ip_link(["set", "dev", device, "txqueuelen", value])
			if res is None:
				log.warning("Cannot set txqueuelen for device '%s'" % device)
				return None
		return value

	def _get_re_ip_link_show(self, arg):
		"""
		Return regex for int arg value from "ip link show" command
		"""
		if arg not in self._re_ip_link_show:
			self._re_ip_link_show[arg] = re.compile(r".*\s+%s\s+(\d+)" % arg)
		return self._re_ip_link_show[arg]

	@command_get("txqueuelen")
	def _get_txqueuelen(self, device, ignore_missing=False):
		out = self._ip_link_show(device)
		if out is None:
			if not ignore_missing:
				log.info("Cannot get 'ip link show' result for txqueuelen value for device '%s'" % device)
			return None
		res = self._get_re_ip_link_show("qlen").search(out)
		if res is None:
			# We can theoretically get device without qlen (http://linux-ip.net/gl/ip-cref/ip-cref-node17.html)
			if not ignore_missing:
				log.info("Cannot get txqueuelen value from 'ip link show' result for device '%s'" % device)
			return None
		return res.group(1)

	@command_set("mtu", per_device=True)
	def _set_mtu(self, value, device, sim, remove):
		if value is None:
			return None
		try:
			int(value)
		except ValueError:
			log.warning("mtu value '%s' is not integer" % value)
			return None
		if not sim:
			res = self._call_ip_link(["set", "dev", device, "mtu", value])
			if res is None:
				log.warning("Cannot set mtu for device '%s'" % device)
				return None
		return value

	@command_get("mtu")
	def _get_mtu(self, device, ignore_missing=False):
		out = self._ip_link_show(device)
		if out is None:
			if not ignore_missing:
				log.info("Cannot get 'ip link show' result for mtu value for device '%s'" % device)
			return None
		res = self._get_re_ip_link_show("mtu").search(out)
		if res is None:
			# mtu value should be always present, but it's better to have a test
			if not ignore_missing:
				log.info("Cannot get mtu value from 'ip link show' result for device '%s'" % device)
			return None
		return res.group(1)

	# d is dict: {parameter: value}
	def _check_parameters(self, context, d):
		if context == "features":
			return True
		params = set(d.keys())
		supported_getter = { "coalesce": self._get_config_options_coalesce, \
				"pause": self._get_config_options_pause, \
				"ring": self._get_config_options_ring, \
				"channels": self._get_config_options_channels }
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

	# parse output of ethtool -l
	def _parse_channels_parameters(self, s):
		a = re.split(r"^Current hardware settings:$", s, flags=re.MULTILINE)
		s = a[1]
		s = self._cmd.multiple_re_replace(\
				{"RX": "rx",
				"TX": "tx",
				"Other": "other",
				"Combined": "combined"}, s)
		l = s.split("\n")
		l = [x for x in l if x != '']
		l = [x for x in [re.split(r":\s*", x) for x in l] if len(x) == 2]
		return dict(l)

	def _replace_channels_parameters(self, context, params_list, dev_params):
		mod_params_list = []
		if "combined" in params_list:
			mod_params_list.extend(["rx", params_list[1], "tx", params_list[1]])
		else:
			cnt = str(max(int(params_list[1]), int(params_list[3])))
			mod_params_list.extend(["combined", cnt])
		return dict(list(zip(mod_params_list[::2], mod_params_list[1::2])))

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
		context2opt = { "coalesce": "-c", "features": "-k", "pause": "-a", "ring": "-g", \
				"channels": "-l"}
		opt = context2opt[context]
		ret, value = self._cmd.execute(["ethtool", opt, device])
		if ret != 0 or len(value) == 0:
			return None
		context2parser = { "coalesce": self._parse_device_parameters, \
				"features": self._parse_device_parameters, \
				"pause": self._parse_pause_parameters, \
				"ring": self._parse_ring_parameters, \
				"channels": self._parse_channels_parameters }
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
			# replace the channel parameters based on the device support
			if context == "channels" and str(dev_params[next(iter(d))]) in ["n/a", "0"]:
				d = self._replace_channels_parameters(context, self._cmd.dict2list(d), dev_params)

		if not sim and len(d) != 0:
			log.debug("setting %s: %s" % (context, str(d)))
			context2opt = { "coalesce": "-C", "features": "-K", "pause": "-A", "ring": "-G", \
                                "channels": "-L"}
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
			if params_current is None or len(params_current) == 0:
				return False
			params_set = self._set_device_parameters(context,
					value, device, verify,
					dev_params = params_current)
			# if none of parameters passed checks then the command completely
			# failed
			if params_set is None or len(params_set) == 0:
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

	@command_custom("channels", per_device = True)
	def _channels(self, start, value, device, verify, ignore_missing):
		return self._custom_parameters("channels", start, value, device, verify)
