import base
from decorators import *
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
		super(self.__class__, self).__init__(*args, **kwargs)
		self._load_smallest = 0.05
		self._level_steps = 6
		self._cmd = commands()

	def _init_devices(self):
		self._devices = set()
		self._assigned_devices = set()

		re_not_virtual = re.compile('(?!.*/virtual/.*)')
		for device in self._hardware_inventory.get_devices("net"):
			if re_not_virtual.match(device.device_path):
				self._devices.add(device.sys_name)

		self._free_devices = self._devices.copy()
		log.debug("devices: %s" % str(self._devices));

	def _instance_init(self, instance):
		instance._has_static_tuning = True
		instance._has_dynamic_tuning = True

		instance._load_monitor = self._monitors_repository.create("net", instance.devices)
		instance._idle = {}
		instance._stats = {}

	def _instance_cleanup(self, instance):
		if instance._load_monitor is not None:
			self._monitors_repository.delete(instance._load_monitor)
			instance._load_monitor = None

	def _instance_apply_dynamic(self, instance, device):
		self._instance_update_dynamic(instance, device)

	def _instance_update_dynamic(self, instance, device):
		load = map(lambda value: int(value), instance._load_monitor.get_device_load(device))
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

	def _get_config_options(cls):
		return {
			"wake_on_lan": None,
			"nf_conntrack_hashsize": None,
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
		diff = map(lambda (new, old): new - old, zip(new_load, old_load))
		instance._stats[device]["diff"] = diff

		# adapt maximum expected load if the difference is higer
		old_max_load = instance._stats[device]["max"]
		max_load = map(lambda pair: max(pair), zip(old_max_load, diff))
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

	@classmethod
	def _nf_conntrack_hashsize_path(self):
		return "/sys/module/nf_conntrack/parameters/hashsize"

	@command_set("wake_on_lan", per_device=True)
	def _set_wake_on_lan(self, value, device):
		if value is None:
			return

		# see man ethtool for possible wol values, 0 added as an alias for 'd'
		value = re.sub(r"0", "d", str(value));
		if not re.match(r"^[" + WOL_VALUES + r"]+$", value):
			log.warn("Incorrect 'wake_on_lan' value.")
			return

		self._cmd.execute(["ethtool", "-s", device, "wol", value])

	@command_get("wake_on_lan")
	def _get_wake_on_lan(self, device):
		value = None
		try:
			m = re.match(r".*Wake-on:\s*([" + WOL_VALUES + "]+).*", self._cmd.execute(["ethtool", device])[1], re.S)
			if m:
				value = m.group(1)
		except IOError:
			pass
		return value

	@command_set("nf_conntrack_hashsize")
	def _set_nf_conntrack_hashsize(self, value):
		if value is None:
			return

		hashsize = int(value)
		if hashsize >= 0:
			self._cmd.write_to_file(self._nf_conntrack_hashsize_path(), hashsize)

	@command_get("nf_conntrack_hashsize")
	def _get_nf_conntrack_hashsize(self):
		value = self._cmd.read_file(self._nf_conntrack_hashsize_path())
		if len(value) > 0:
			return int(value)
		return None
