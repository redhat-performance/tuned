import os, copy
import tuned.plugins
import tuned.logs
import tuned.monitors
import tuned.utils.commands
import struct

log = tuned.logs.get()

class DiskPlugin(tuned.plugins.Plugin):

	_supported_vendors = ["ATA", "SCSI"]

	def __init__(self, devices, options):
		"""
		"""
		super(self.__class__, self).__init__(None, options)

		self.devidle = {}
		self.stats = {}
		self.power = ["255", "225", "195", "165", "145", "125", "105", "85", "70", "55", "30", "20"]
		self.spindown = ["0", "250", "230", "210", "190", "170", "150", "130", "110", "90", "70", "60"]
		self.levels = len(self.power)
		self._elevator_set = False
		self._old_elevator = ""

		self._load_monitor = tuned.monitors.get_repository().create("disk", devices)

		if not tuned.utils.storage.Storage.get_instance().data.has_key("disk"):
			tuned.utils.storage.Storage.get_instance().data["disk"] = {}

	@classmethod
	def tunable_devices(cls):
		block_devices = os.listdir("/sys/block")
		available = set(filter(cls._is_device_supported, block_devices))
		cls._available_devices = available

	@classmethod
	def _is_device_supported(cls, device):
		vendor_file = "/sys/block/%s/device/vendor" % device
		try:
			vendor = open(vendor_file).read().strip()
		except IOError:
			return False

		return vendor in cls._supported_vendors

	@classmethod
	def _get_default_options(cls):
		return {
			"elevator"   : "",
			"disk_alpm"  : "",
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

		tuned.monitors.get_repository().delete(self._load_monitor)

		for dev in self.devidle.keys():
			if self.devidle[dev]["LEVEL"] > 0:
				os.system("hdparm -S0 -B255 /dev/"+dev+" > /dev/null 2>&1")
			self._revert_elevator(dev)

		self._revert_disk_alpm()

	def update_tuning(self):
		load = self._load_monitor.get_load()
		for dev, devload in load.iteritems():
			if not self._elevator_set:
				self._apply_elevator(dev)

			self._init_stats(dev)
			self._update_stats(dev, devload)
			self._update_idle(dev)

			if self.devidle[dev]["LEVEL"] < self.levels-1 and self.devidle[dev]["read"] >= 6 and self.devidle[dev]["write"] >= 6:
				self.devidle[dev].setdefault("LEVEL", 0)
				self.devidle[dev]["LEVEL"] += 1
				level = self.devidle[dev]["LEVEL"]

				log.debug("Level changed to %d (power %s, spindown %s)" % (level, self.power[level], self.spindown[level]))
				os.system("hdparm -S"+self.power[level]+" -B"+self.spindown[level]+" /dev/"+dev+" > /dev/null 2>&1")

			if self.devidle[dev]["LEVEL"] > 0 and (self.devidle[dev]["read"] == 0 or self.devidle[dev]["write"] == 0):
				self.devidle[dev].setdefault("LEVEL", 0)
				self.devidle[dev]["LEVEL"] -= 2
				if self.devidle[dev]["LEVEL"] < 0:
					self.devidle[dev]["LEVEL"] = 0
				level = self.devidle[dev]["LEVEL"]

				log.debug("Level changed to %d (power %s, spindown %s)" % (level, self.power[level], self.spindown[level]))
				os.system("hdparm -S"+self.power[level]+" -B"+self.spindown[level]+" /dev/"+dev+" > /dev/null 2>&1")

			log.debug("%s load: read %f, write %f" % (dev, self.stats[dev]["read"], self.stats[dev]["write"]))
			log.debug("%s idle: read %d, write %d, level %d" % (dev, self.devidle[dev]["read"], self.devidle[dev]["write"], self.devidle[dev]["LEVEL"]))

		if not self._elevator_set:
			self._apply_disk_alpm()

		self._elevator_set = True

	# Commands:

	def _apply_elevator(self, dev):
		sys_file = os.path.join("/sys/block/", dev, "queue/scheduler")
		tuned.utils.commands.revert_file("disk", "elevator_" + dev, sys_file)

		if len(self._options["elevator"]) == 0:
			return False

		tuned.utils.commands.set_file("disk", "elevator_" + dev, sys_file, self._options["elevator"])
		return True

	def _revert_elevator(self, dev):
		sys_file = os.path.join("/sys/block/", dev, "queue/scheduler")
		tuned.utils.commands.revert_file("disk", "elevator_" + dev, sys_file)

	def _apply_disk_alpm(self):
		for host in os.listdir("/sys/class/scsi_host/"):
			sys_file = os.path.join("/sys/class/scsi_host/", host, "link_power_management_policy")
			tuned.utils.commands.revert_file("disk", "disk_alpm", sys_file)

		if len(self._options["disk_alpm"]) == 0:
			return False

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

			policy = self._options["disk_alpm"]
			if port_cmd_int & 24000 != 0:
				policy = "max_performance"

			sys_file = os.path.join("/sys/class/scsi_host/", host, "link_power_management_policy")
			tuned.utils.commands.set_file("disk", "disk_alpm", sys_file, policy)

		return True

	def _revert_disk_alpm(self):
		for host in os.listdir("/sys/class/scsi_host/"):
			sys_file = os.path.join("/sys/class/scsi_host/", host, "link_power_management_policy")
			tuned.utils.commands.revert_file("disk", "disk_alpm", sys_file)
