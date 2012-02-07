import os, copy
import tuned.plugins
import tuned.logs
import tuned.monitors
import struct

log = tuned.logs.get()

class DiskPlugin(tuned.plugins.Plugin):

	_supported_vendors = ["ATA", "SCSI"]

	def __init__(self, devices, options):
		"""
		"""
		super(self.__class__, self).__init__(None, options)

		self.devidle = {}
		self.power = ["255", "225", "195", "165", "145", "125", "105", "85", "70", "55", "30", "20"]
		self.spindown = ["0", "250", "230", "210", "190", "170", "150", "130", "110", "90", "70", "60"]
		self.levels = len(self.power)

		self._load_monitor = tuned.monitors.get_repository().create("disk", devices)

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

	def _updateIdle(self, dev, devload):
		idle = self.devidle.setdefault(dev, {})
		idle.setdefault("LEVEL", 0)
		for type in ("READ", "WRITE"):
			if devload[type] == 0.0:
				idle.setdefault(type, 0)
				idle[type] += 1
			else:
				idle.setdefault(type, 0)
				idle[type] = 0


	def cleanup(self):
		log.debug("Cleanup")

		for dev in self.devidle.keys():
			if self.devidle[dev]["LEVEL"] > 0:
				os.system("hdparm -S0 -B255 /dev/"+dev+" > /dev/null 2>&1")

	def update_tuning(self):
		load = self._load_monitor.get_load()
		for dev, devload in load.iteritems():
			self._updateIdle(dev, devload)

			if self.devidle[dev]["LEVEL"] < self.levels-1 and self.devidle[dev]["READ"] >= 6 and self.devidle[dev]["WRITE"] >= 6:
				self.devidle[dev].setdefault("LEVEL", 0)
				self.devidle[dev]["LEVEL"] += 1
				level = self.devidle[dev]["LEVEL"]

				log.debug("Level changed to %d (power %s, spindown %s)" % (level, self.power[level], self.spindown[level]))
				os.system("hdparm -S"+self.power[level]+" -B"+self.spindown[level]+" /dev/"+dev+" > /dev/null 2>&1")

			if self.devidle[dev]["LEVEL"] > 0 and (self.devidle[dev]["READ"] == 0 or self.devidle[dev]["WRITE"] == 0):
				self.devidle[dev].setdefault("LEVEL", 0)
				self.devidle[dev]["LEVEL"] -= 2
				if self.devidle[dev]["LEVEL"] < 0:
					self.devidle[dev]["LEVEL"] = 0
				level = self.devidle[dev]["LEVEL"]

				log.debug("Level changed to %d (power %s, spindown %s)" % (level, self.power[level], self.spindown[level]))
				os.system("hdparm -S"+self.power[level]+" -B"+self.spindown[level]+" /dev/"+dev+" > /dev/null 2>&1")

			log.debug("%s load: read %f, write %f" % (dev, load[dev]["READ"], load[dev]["WRITE"]))
			log.debug("%s idle: read %d, write %d, level %d" % (dev, self.devidle[dev]["READ"], self.devidle[dev]["WRITE"], self.devidle[dev]["LEVEL"]))
