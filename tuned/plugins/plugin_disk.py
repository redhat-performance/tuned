import errno
from . import hotplug
from .decorators import *
import tuned.logs
import tuned.consts as consts
from tuned.utils.commands import commands
import os
import re

log = tuned.logs.get()

class DiskPlugin(hotplug.Plugin):
	"""
	Plug-in for tuning various block device options. This plug-in can also
	dynamically change the advanced power management and spindown timeout
	setting for a drive according to the current drive utilization. The
	dynamic tuning is controlled by the [option]`dynamic` and the global
	[option]`dynamic_tuning` option in `tuned-main.conf`.

	The disk plug-in operates on all supported block devices unless a
	comma separated list of [option]`devices` is passed to it.

	.Operate only on the `sda` block device
	====
	----
	[disk]
	devices=sda
	----
	====

	The [option]`elevator` option sets the Linux I/O scheduler.

	.Use the bfq I/O scheduler on the `xvda` block device
	====
	----
	[disk]
	device=xvda
	elevator=bfq
	----
	====

	The [option]`scheduler_quantum` option only applies to the CFQ I/O
	scheduler. It defines the number of I/O requests that CFQ sends to
	one device at one time, essentially limiting queue depth. The default
	value is 8 requests. The device being used may support greater queue
	depth, but increasing the value of quantum will also increase latency,
	especially for large sequential write work loads.

	The [option]`apm` option sets the Advanced Power Management feature
	on drives that support it. It corresponds to using the `-B` option of
	the `hdparm` utility. The [option]`spindown` option puts the drive
	into idle (low-power) mode, and also sets the standby (spindown)
	timeout for the drive. It corresponds to using `-S` option of the
	`hdparm` utility.

	.Use a medium-agressive power management with spindown
	====
	----
	[disk]
	apm=128
	spindown=6
	----
	====

	The [option]`readahead` option controls how much extra data the
	operating system reads from disk when performing sequential
	I/O operations. Increasing the `readahead` value might improve
	performance in application environments where sequential reading of
	large files takes place. The default unit for readahead is KiB. This
	can be adjusted to sectors by specifying the suffix 's'. If the
	suffix is specified, there must be at least one space between the
	number and suffix (for example, `readahead=8192 s`).

	.Set the `readahead` to 4MB unless already set to a higher value
	====
	----
	[disk]
	readahead=>4096
	----
	====
	The disk readahead value can be multiplied by the constant
	specified by the [option]`readahead_multiply` option.
	"""

	def __init__(self, *args, **kwargs):
		super(DiskPlugin, self).__init__(*args, **kwargs)

		self._power_levels = [254, 225, 195, 165, 145, 125, 105, 85, 70, 55, 30, 20]
		self._spindown_levels = [0, 250, 230, 210, 190, 170, 150, 130, 110, 90, 70, 60]
		self._levels = len(self._power_levels)
		self._level_steps = 6
		self._load_smallest = 0.01
		self._cmd = commands()

	def _init_devices(self):
		super(DiskPlugin, self)._init_devices()
		self._devices_supported = True
		self._use_hdparm = True
		self._free_devices = set()
		self._hdparm_apm_device_support = dict()
		for device in self._hardware_inventory.get_devices("block"):
			if self._device_is_supported(device):
				self._free_devices.add(device.sys_name)
		self._assigned_devices = set()

	def _get_device_objects(self, devices):
		return [self._hardware_inventory.get_device("block", x) for x in devices]

	def _is_hdparm_apm_supported(self, device):
		if not self._use_hdparm:
			return False
		if device in self._hdparm_apm_device_support:
			return self._hdparm_apm_device_support[device]
		(rc, out, err_msg) = self._cmd.execute(["hdparm", "-C", "/dev/%s" % device], \
				no_errors = [errno.ENOENT], return_err=True)
		if rc == -errno.ENOENT:
			log.warning("hdparm command not found, ignoring for other devices")
			self._use_hdparm = False
			return False
		elif rc:
			log.info("Device '%s' not supported by hdparm" % device)
			log.debug("(rc: %s, msg: '%s')" % (rc, err_msg))
			self._hdparm_apm_device_support[device] = False
			return False
		elif "unknown" in out:
			log.info("Driver for device '%s' does not support apm command" % device)
			self._hdparm_apm_device_support[device] = False
			return False
		self._hdparm_apm_device_support[device] = True
		return True

	@classmethod
	def _device_is_supported(cls, device):
		return  device.device_type == "disk" and \
			device.attributes.get("removable", None) == b"0" and \
			(device.parent is None or \
					device.parent.subsystem in ["scsi", "virtio", "xen", "nvme"])

	def _hardware_events_init(self):
		self._hardware_inventory.subscribe(self, "block", self._hardware_events_callback)

	def _hardware_events_cleanup(self):
		self._hardware_inventory.unsubscribe(self)

	def _hardware_events_callback(self, event, device):
		if self._device_is_supported(device) or event == "remove":
			super(DiskPlugin, self)._hardware_events_callback(event, device)

	def _added_device_apply_tuning(self, instance, device_name):
		if instance._load_monitor is not None:
			instance._load_monitor.add_device(device_name)
		super(DiskPlugin, self)._added_device_apply_tuning(instance, device_name)

	def _removed_device_unapply_tuning(self, instance, device_name):
		if instance._load_monitor is not None:
			instance._load_monitor.remove_device(device_name)
		super(DiskPlugin, self)._removed_device_unapply_tuning(instance, device_name)

	@classmethod
	def _get_config_options(cls):
		return {
			"dynamic"            : True, # FIXME: do we want this default?
			"elevator"           : None,
			"apm"                : None,
			"spindown"           : None,
			"readahead"          : None,
			"readahead_multiply" : None,
			"scheduler_quantum"  : None,
		}

	@classmethod
	def _get_config_options_used_by_dynamic(cls):
		return [
			"apm",
			"spindown",
		]

	def _instance_init(self, instance):
		instance._has_static_tuning = True

		self._apm_errcnt = 0
		self._spindown_errcnt = 0

		instance._load_monitor = None
		instance._has_dynamic_tuning = self._option_bool(instance.options["dynamic"])

	def _instance_cleanup(self, instance):
		if instance._load_monitor is not None:
			self._monitors_repository.delete(instance._load_monitor)
			instance._load_monitor = None

	def _instance_init_dynamic(self, instance):
		super(DiskPlugin, self)._instance_init_dynamic(instance)
		instance._device_idle = {}
		instance._stats = {}
		instance._idle = {}
		instance._spindown_change_delayed = {}
		instance._load_monitor = self._monitors_repository.create(
						"disk", instance.assigned_devices)

	def _update_errcnt(self, rc, spindown):
		if spindown:
			s = "spindown"
			cnt = self._spindown_errcnt
		else:
			s = "apm"
			cnt = self._apm_errcnt
		if cnt >= consts.ERROR_THRESHOLD:
			return
		if rc == 0:
			cnt = 0
		elif rc == -errno.ENOENT:
			self._spindown_errcnt = self._apm_errcnt = consts.ERROR_THRESHOLD + 1
			log.warning("hdparm command not found, ignoring future set_apm / set_spindown commands")
			return
		else:
			cnt += 1
			if cnt == consts.ERROR_THRESHOLD:
				log.info("disabling set_%s command: too many consecutive errors" % s)
		if spindown:
			self._spindown_errcnt = cnt
		else:
			self._apm_errcnt = cnt

	def _change_spindown(self, instance, device, new_spindown_level):
		log.debug("changing spindown to %d" % new_spindown_level)
		(rc, out) = self._cmd.execute(["hdparm", "-S%d" % new_spindown_level, "/dev/%s" % device], no_errors = [errno.ENOENT])
		self._update_errcnt(rc, True)
		instance._spindown_change_delayed[device] = False

	def _drive_spinning(self, device):
		(rc, out) = self._cmd.execute(["hdparm", "-C", "/dev/%s" % device], no_errors = [errno.ENOENT])
		return not "standby" in out and not "sleeping" in out

	def _instance_update_dynamic(self, instance, device):
		if not self._is_hdparm_apm_supported(device):
			return
		load = instance._load_monitor.get_device_load(device)
		if load is None:
			return

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

			log.debug("tuning level changed to %d" % idle["level"])
			if self._spindown_errcnt < consts.ERROR_THRESHOLD:
				if not self._drive_spinning(device) and level_change > 0:
					log.debug("delaying spindown change to %d, drive has already spun down" % new_spindown_level)
					instance._spindown_change_delayed[device] = True
				else:
					self._change_spindown(instance, device, new_spindown_level)
			if self._apm_errcnt < consts.ERROR_THRESHOLD:
				log.debug("changing APM_level to %d" % new_power_level)
				(rc, out) = self._cmd.execute(["hdparm", "-B%d" % new_power_level, "/dev/%s" % device], no_errors = [errno.ENOENT])
				self._update_errcnt(rc, False)
		elif instance._spindown_change_delayed[device] and self._drive_spinning(device):
			new_spindown_level = self._spindown_levels[idle["level"]]
			self._change_spindown(instance, device, new_spindown_level)

		log.debug("%s load: read %0.2f, write %0.2f" % (device, stats["read"], stats["write"]))
		log.debug("%s idle: read %d, write %d, level %d" % (device, idle["read"], idle["write"], idle["level"]))

	def _init_stats_and_idle(self, instance, device):
		instance._stats[device] = { "new": 11 * [0], "old": 11 * [0], "max": 11 * [1] }
		instance._idle[device] = { "level": 0, "read": 0, "write": 0 }
		instance._spindown_change_delayed[device] = False

	def _update_stats(self, instance, device, new_load):
		instance._stats[device]["old"] = old_load = instance._stats[device]["new"]
		instance._stats[device]["new"] = new_load

		# load difference
		diff = [new_old[0] - new_old[1] for new_old in zip(new_load, old_load)]
		instance._stats[device]["diff"] = diff

		# adapt maximum expected load if the difference is higher
		old_max_load = instance._stats[device]["max"]
		max_load = [max(pair) for pair in zip(old_max_load, diff)]
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

	def _instance_apply_dynamic(self, instance, device):
		# At the moment we support dynamic tuning just for devices compatible with hdparm apm commands
		# If in future will be added new functionality not connected to this command,
		# it is needed to change it here
		if not self._is_hdparm_apm_supported(device):
			log.info("There is no dynamic tuning available for device '%s' at time" % device)
		else:
			super(DiskPlugin, self)._instance_apply_dynamic(instance, device)

	def _instance_unapply_dynamic(self, instance, device):
		pass

	def _sysfs_path(self, device, suffix, prefix = "/sys/block/"):
		if "/" in device:
			dev = os.path.join(prefix, device.replace("/", "!"), suffix)
			if os.path.exists(dev):
				return dev
		return os.path.join(prefix, device, suffix)

	def _elevator_file(self, device):
		return self._sysfs_path(device, "queue/scheduler")

	@command_set("elevator", per_device=True)
	def _set_elevator(self, value, device, sim, remove):
		sys_file = self._elevator_file(device)
		if not sim:
			self._cmd.write_to_file(sys_file, value, \
				no_error = [errno.ENOENT] if remove else False)
		return value

	@command_get("elevator")
	def _get_elevator(self, device, ignore_missing=False):
		sys_file = self._elevator_file(device)
		# example of scheduler file content:
		# noop deadline [cfq]
		return self._cmd.get_active_option(self._cmd.read_file(sys_file, no_error=ignore_missing))

	@command_set("apm", per_device=True)
	def _set_apm(self, value, device, sim, remove):
		if not self._is_hdparm_apm_supported(device):
			if not sim:
				log.info("apm option is not supported for device '%s'" % device)
				return None
			else:
				return str(value)
		if self._apm_errcnt < consts.ERROR_THRESHOLD:
			if not sim:
				(rc, out) = self._cmd.execute(["hdparm", "-B", str(value), "/dev/" + device], no_errors = [errno.ENOENT])
				self._update_errcnt(rc, False)
			return str(value)
		else:
			return None

	@command_get("apm")
	def _get_apm(self, device, ignore_missing=False):
		if not self._is_hdparm_apm_supported(device):
			if not ignore_missing:
				log.info("apm option is not supported for device '%s'" % device)
			return None
		value = None
		err = False
		(rc, out) = self._cmd.execute(["hdparm", "-B", "/dev/" + device], no_errors = [errno.ENOENT])
		if rc == -errno.ENOENT:
			return None
		elif rc != 0:
			err = True
		else:
			m = re.match(r".*=\s*(\d+).*", out, re.S)
			if m:
				try:
					value = int(m.group(1))
				except ValueError:
					err = True
		if err:
			log.error("could not get current APM settings for device '%s'" % device)
		return value

	@command_set("spindown", per_device=True)
	def _set_spindown(self, value, device, sim, remove):
		if not self._is_hdparm_apm_supported(device):
			if not sim:
				log.info("spindown option is not supported for device '%s'" % device)
				return None
			else:
				return str(value)
		if self._spindown_errcnt < consts.ERROR_THRESHOLD:
			if not sim:
				(rc, out) = self._cmd.execute(["hdparm", "-S", str(value), "/dev/" + device], no_errors = [errno.ENOENT])
				self._update_errcnt(rc, True)
			return str(value)
		else:
			return None

	@command_get("spindown")
	def _get_spindown(self, device, ignore_missing=False):
		if not self._is_hdparm_apm_supported(device):
			if not ignore_missing:
				log.info("spindown option is not supported for device '%s'" % device)
			return None
		# There's no way how to get current/old spindown value, hardcoding vendor specific 253
		return 253

	def _readahead_file(self, device):
		return self._sysfs_path(device, "queue/read_ahead_kb")

	def _parse_ra(self, value):
		val = str(value).split(None, 1)
		try:
			v = int(val[0])
		except ValueError:
			return None
		if len(val) > 1 and val[1][0] == "s":
			# v *= 512 / 1024
			v /= 2
		return v

	@command_set("readahead", per_device=True)
	def _set_readahead(self, value, device, sim, remove):
		sys_file = self._readahead_file(device)
		val = self._parse_ra(value)
		if val is None:
			log.error("Invalid readahead value '%s' for device '%s'" % (value, device))
		else:
			if not sim:
				self._cmd.write_to_file(sys_file, "%d" % val, \
					no_error = [errno.ENOENT] if remove else False)
		return val

	@command_get("readahead")
	def _get_readahead(self, device, ignore_missing=False):
		sys_file = self._readahead_file(device)
		value = self._cmd.read_file(sys_file, no_error=ignore_missing).strip()
		if len(value) == 0:
			return None
		return int(value)

	@command_custom("readahead_multiply", per_device=True)
	def _multiply_readahead(self, enabling, multiplier, device, verify, ignore_missing):
		if verify:
			return None
		storage_key = self._storage_key(
				command_name = "readahead_multiply",
				device_name = device)
		if enabling:
			old_readahead = self._get_readahead(device)
			if old_readahead is None:
				return
			new_readahead = int(float(multiplier) * old_readahead)
			self._storage.set(storage_key, old_readahead)
			self._set_readahead(new_readahead, device, False)
		else:
			old_readahead = self._storage.get(storage_key)
			if old_readahead is None:
				return
			self._set_readahead(old_readahead, device, False)
			self._storage.unset(storage_key)

	def _scheduler_quantum_file(self, device):
		return self._sysfs_path(device, "queue/iosched/quantum")

	@command_set("scheduler_quantum", per_device=True)
	def _set_scheduler_quantum(self, value, device, sim, remove):
		sys_file = self._scheduler_quantum_file(device)
		if not sim:
			self._cmd.write_to_file(sys_file, "%d" % int(value), \
				no_error = [errno.ENOENT] if remove else False)
		return value

	@command_get("scheduler_quantum")
	def _get_scheduler_quantum(self, device, ignore_missing=False):
		sys_file = self._scheduler_quantum_file(device)
		value = self._cmd.read_file(sys_file, no_error=ignore_missing).strip()
		if len(value) == 0:
			if not ignore_missing:
				log.info("disk_scheduler_quantum option is not supported for device '%s'" % device)
			return None
		return int(value)
