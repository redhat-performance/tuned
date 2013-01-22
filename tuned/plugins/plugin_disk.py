import base
from decorators import *
import tuned.logs
import tuned.utils.commands
import os
import re

log = tuned.logs.get()

class DiskPlugin(base.Plugin):
	"""
	Plugin for tuning options of disks.
	"""

	def __init__(self, *args, **kwargs):
		super(self.__class__, self).__init__(*args, **kwargs)

		self._power_levels = [255, 225, 195, 165, 145, 125, 105, 85, 70, 55, 30, 20]
		self._spindown_levels = [0, 250, 230, 210, 190, 170, 150, 130, 110, 90, 70, 60]
		self._levels = len(self._power_levels)
		self._level_steps = 6
		self._load_smallest = 0.01

	def _init_devices(self):
		self._devices = set()
		for device in self._hardware_inventory.get_devices("block"):
			if self._device_is_supported(device):
				self._devices.add(device.sys_name)

		self._assigned_devices = set()
		self._free_devices = self._devices.copy()

	def _device_is_supported(cls, device):
		return  device.device_type == "disk" \
			and device.attributes.get("removable", None) == "0" \
			and device.parent is not None \
			and device.parent.subsystem in ["scsi", "virtio"]

	def _get_config_options(cls):
		return {
			"dynamic"            : True, # FIXME: do we want this default?
			"elevator"           : None,
			"alpm"               : None,
			"apm"                : None,
			"spindown"           : None,
			"readahead"          : None,
			"readahead_multiply" : None,
			"scheduler_quantum"  : None,
		}

	def _instance_init(self, instance):
		instance._has_static_tuning = True

		if self._option_bool(instance.options["dynamic"]):
			instance._has_dynamic_tuning = True
			instance._load_monitor = self._monitors_repository.create("disk", instance.devices)
			instance._device_idle = {}
			instance._stats = {}
			instance._idle = {}
		else:
			instance._has_dynamic_tuning = False
			instance._load_monitor = None

	def _instance_cleanup(self, instance):
		if instance._load_monitor is not None:
			self._monitors_repository.delete(instance._load_monitor)
			instance._load_monitor = None

	def _instance_apply_dynamic(self, instance, device):
		pass

	def instance_update_tuning(self, instance):
		instance.current_load = instance._load_monitor.get_load()
		super(self.__class__, self).instance_update_tuning(instance)

	def _instance_update_dynamic(self, instance, device):
		if not device in instance.current_load:
			return

		load = instance.current_load[device]
		if not device in instance._stats:
			self._init_stats_and_idle(instance, device)

		self._update_stats(instance, device, load)
		self._update_idle(instance, device)

		stats = instance._stats[device]
		idle = instance._idle[device]

		# level change decision

		if idle["level"] + 1 < self._levels and idle["read"] >= self._level_steps and idle["write"] >= self._level_steps:
			level_change = 1
		elif idle["level"] > 0 and (idle["read"] == 0 or idle["write"] == 0):
			level_change = -1
		else:
			level_change = 0

		# change level if decided

		if level_change != 0:
			idle["level"] += level_change
			new_power_level = self._power_levels[idle["level"]]
			new_spindown_level = self._spindown_levels[idle["level"]]

			log.debug("tuning level changed to %d (power %d, spindown %d)" % (idle["level"], new_power_level, new_spindown_level))
			tuned.utils.commands.execute(["hdparm", "-S%d" % new_spindown_level, "-B%d" % new_power_level, "/dev/%s" % device])

		log.debug("%s load: read %0.2f, write %0.2f" % (device, stats["read"], stats["write"]))
		log.debug("%s idle: read %d, write %d, level %d" % (device, idle["read"], idle["write"], idle["level"]))

	def _init_stats_and_idle(self, instance, device):
		instance._stats[device] = { "new": 11 * [0], "old": 11 * [0], "max": 11 * [1] }
		instance._idle[device] = { "level": 0, "read": 0, "write": 0 }

	def _update_stats(self, instance, device, new_load):
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
		instance._stats[device]["read"] =  float(diff[1]) / float(max_load[1])
		instance._stats[device]["write"] = float(diff[5]) / float(max_load[5])

	def _update_idle(self, instance, device):
		# increase counter if there is no load, otherwise reset the counter
		for operation in ["read", "write"]:
			if instance._stats[device][operation] < self._load_smallest:
				instance._idle[device][operation] += 1
			else:
				instance._idle[device][operation] = 0

	def _instance_unapply_dynamic(self, instance, device):
		if device in instance._idle and instance._idle[device]["level"] > 0:
			log.debug("%s restoring power and spindown settings" % device)
			tuned.utils.commands.execute(["hdparm", "-S0", "-B255", "/dev/%s" % device])

	def _elevator_file(self, device):
		return os.path.join("/sys/block/", device, "queue/scheduler")

	@command_set("elevator", per_device=True)
	def _set_elevator(self, value, device):
		sys_file = self._elevator_file(device)
		tuned.utils.commands.write_to_file(sys_file, value)

	@command_get("elevator")
	def _get_elevator(self, device):
		sys_file = self._elevator_file(device)
		# example of scheduler file content:
		# noop deadline [cfq]
		return tuned.utils.commands.get_active_option(tuned.utils.commands.read_file(sys_file))

	def _alpm_policy_files(self):
		policy_files = []
		for host in os.listdir("/sys/class/scsi_host/"):
			port_cmd_path = os.path.join("/sys/class/scsi_host/", host, "ahci_port_cmd")
			try:
				port_cmd = open(port_cmd_path).read().strip()
			except (OSError,IOError) as e:
				log.error("Reading %s error: %s" % (port_cmd_path, e))
				continue
			try:
				port_cmd_int = int("0x" + port_cmd, 16)
			except ValueError:
				log.error("Unexpected value in %s" % (port_cmd_path))
				continue

			policy_file = os.path.join("/sys/class/scsi_host/", host, "link_power_management_policy")
			policy_files.append(policy_file)

		return policy_files

	@command_set("alpm")
	def _set_alpm(self, policy):
		for policy_file in self._alpm_policy_files():
			tuned.utils.commands.write_to_file(policy_file, policy)

	@command_get("alpm")
	def _get_alpm(self):
		for policy_file in self._alpm_policy_files():
			return tuned.utils.commands.read_file(policy_file)
		return None

	@command_set("apm", per_device=True)
	def _set_apm(self, value, device):
		tuned.utils.commands.execute(["hdparm", "-B", str(value), "/dev/" + device])

	@command_get("apm")
	def _get_apm(self, device):
		value = None
		try:
			m = re.match(r".*=\s*(\d+).*", tuned.utils.commands.execute(["hdparm", "-B", "/dev/" + device]), re.S)
			if m:
				value = int(m.group(1))
		except:
			log.error("could not get current APM settings for device '%s'" % device)
		return value

	@command_set("spindown", per_device=True)
	def _set_spindown(self, value, device):
		tuned.utils.commands.execute(["hdparm", "-S", str(value), "/dev/" + device])

	@command_get("spindown")
	def _get_spindown(self, device):
		# There's no way how to get current/old spindown value, hardcoding vendor specific 253
		return 253

	def _readahead_file(self, device):
		return os.path.join("/sys/block/", device, "queue/read_ahead_kb")

	@command_set("readahead", per_device=True)
	def _set_readahead(self, value, device):
		sys_file = self._readahead_file(device)
		tuned.utils.commands.write_to_file(sys_file, "%d" % int(value))

	@command_get("readahead")
	def _get_readahead(self, device):
		sys_file = self._readahead_file(device)
		value = tuned.utils.commands.read_file(sys_file).strip()
		if len(value) == 0:
			return None
		return int(value)

	@command_custom("readahead_multiply", per_device=True)
	def _multiply_readahead(self, enabling, multiplier, device):
		storage_key = self._storage_key("readahead_multiply", device)
		if enabling:
			old_readahead = self._get_readahead(device)
			if old_readahead is None:
				return
			new_readahead = int(float(multiplier) * old_readahead)
			self._storage.set(storage_key, old_readahead)
			self._set_readahead(new_readahead, device)
		else:
			old_readahead = self._storage.get(storage_key)
			if old_readahead is None:
				return
			self._set_readahead(old_readahead, device)
			self._storage.unset(storage_key)

	def _scheduler_quantum_file(self, device):
		return os.path.join("/sys/block/", device, "queue/iosched/quantum")

	@command_set("scheduler_quantum", per_device=True)
	def _set_scheduler_quantum(self, value, device):
		sys_file = self._scheduler_quantum_file(device)
		tuned.utils.commands.write_to_file(sys_file, "%d" % int(value))

	@command_get("scheduler_quantum")
	def _get_scheduler_quantum(self, device):
		sys_file = self._scheduler_quantum_file(device)
		value = tuned.utils.commands.read_file(sys_file).strip()
		if len(value) == 0:
			log.info("disk_scheduler_quantum option is not supported by this HW")
			return None
		return int(value)
