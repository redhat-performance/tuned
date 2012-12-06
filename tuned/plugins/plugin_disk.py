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

	@classmethod
	def device_requirements(cls):
		return {
			"subsystem": "block",
			"device_type": "disk",
			"custom": cls._is_supported_disk,
		}

	@classmethod
	def _is_supported_disk(cls, device):
		return device.attributes["removable"] == "0" \
			and device.parent is not None and device.parent.subsystem in ["scsi", "virtio"]

	def _post_init(self):
		self.devidle = {}
		self.stats = {}
		self.power = ["255", "225", "195", "165", "145", "125", "105", "85", "70", "55", "30", "20"]
		self.spindown = ["0", "250", "230", "210", "190", "170", "150", "130", "110", "90", "70", "60"]
		self.levels = len(self.power)

		if self._option_bool(self._options["dynamic"]):
			self._load_monitor = self._monitors_repository.create("disk", self._devices)
		else:
			self._dynamic_tuning = False

	@classmethod
	def _get_default_options(cls):
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

	def _update_idle(self, dev):
		idle = self.devidle.setdefault(dev, {})
		idle.setdefault("LEVEL", 0)
		for type in ("read", "write"):
			if self.stats[dev][type] == 0.0:
				idle.setdefault(type, 0)
				idle[type] += 1
			else:
				idle.setdefault(type, 0)
				idle[type] = 0

	def _init_stats(self, dev):
		if not self.stats.has_key(dev):
			self.stats[dev] = {}
			self.stats[dev]["new"] = ['0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0']
			self.stats[dev]["old"] = ['0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0']
			self.stats[dev]["max"] = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

	def _calc_diff(self, dev):
		l = []
		for i in xrange(len(self.stats[dev]["old"])):
			l.append(int(self.stats[dev]["new"][i]) - int(self.stats[dev]["old"][i]))
		return l

	def _update_stats(self, dev, devload):
		self.stats[dev]["old"] = self.stats[dev]["new"]
		self.stats[dev]["new"] = devload
		l = self._calc_diff(dev)
		for i in xrange(len(l)):
			if l[i] > self.stats[dev]["max"][i]:
				self.stats[dev]["max"][i] = l[i]

		self.stats[dev]["diff"] = l

		self.stats[dev]["read"] = float(self.stats[dev]["diff"][1]) / float(self.stats[dev]["max"][1])
		self.stats[dev]["write"] = float(self.stats[dev]["diff"][5]) / float(self.stats[dev]["max"][5])

	def cleanup(self):
		log.debug("Cleanup")

		if self._load_monitor:
			self._monitors_repository.delete(self._load_monitor)

			for dev in self.devidle.keys():
				if self.devidle[dev]["LEVEL"] > 0:
					os.system("hdparm -S0 -B255 /dev/"+dev+" > /dev/null 2>&1")

	def update_tuning(self):
		load = self._load_monitor.get_load()
		for dev, devload in load.iteritems():
			self._init_stats(dev)
			self._update_stats(dev, devload)
			self._update_idle(dev)

			if self.devidle[dev]["LEVEL"] < self.levels-1 and self.devidle[dev]["read"] >= 6 and self.devidle[dev]["write"] >= 6:
				self.devidle[dev].setdefault("LEVEL", 0)
				self.devidle[dev]["LEVEL"] += 1
				level = self.devidle[dev]["LEVEL"]

				log.debug("Level changed to %d (power %s, spindown %s)" % (level, self.power[level], self.spindown[level]))
				os.system("hdparm -S"+self.spindown[level]+" -B"+self.power[level]+" /dev/"+dev+" > /dev/null 2>&1")

			if self.devidle[dev]["LEVEL"] > 0 and (self.devidle[dev]["read"] == 0 or self.devidle[dev]["write"] == 0):
				self.devidle[dev].setdefault("LEVEL", 0)
				self.devidle[dev]["LEVEL"] -= 2
				if self.devidle[dev]["LEVEL"] < 0:
					self.devidle[dev]["LEVEL"] = 0
				level = self.devidle[dev]["LEVEL"]

				log.debug("Level changed to %d (power %s, spindown %s)" % (level, self.power[level], self.spindown[level]))
				os.system("hdparm -S"+self.spindown[level]+" -B"+self.power[level]+" /dev/"+dev+" > /dev/null 2>&1")

			log.debug("%s load: read %f, write %f" % (dev, self.stats[dev]["read"], self.stats[dev]["write"]))
			log.debug("%s idle: read %d, write %d, level %d" % (dev, self.devidle[dev]["read"], self.devidle[dev]["write"], self.devidle[dev]["LEVEL"]))

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
