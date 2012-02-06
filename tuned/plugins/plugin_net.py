import tuned.plugins
import tuned.logs
import tuned.monitors
from tuned.utils.nettool import ethcard
import os
import struct
import copy

log = tuned.logs.get()

class NetTuningPlugin(tuned.plugins.Plugin):
	def __init__(self, devices, options):
		"""
		"""
		super(self.__class__, self).__init__(None, options)

		self.devidle = {}
		log.info("Devices: %s" % str(devices));
		self._load_monitor = tuned.monitors.get_repository().create("net", devices)

	@classmethod
	def tunable_devices(cls):
		available = []
		for root, dirs, files in os.walk("/sys/devices"):
			if root.endswith("/net") and not root.endswith("/virtual/net"):
				available += dirs
		log.info("Tunable devices: %s" % str(available))
		return available

	def _updateIdle(self, dev, devload):
		idle = self.devidle.setdefault(dev, {})
		idle.setdefault("LEVEL", 0)
		for _type in ("READ", "WRITE"):
			if devload[_type] <= 0.05:
				idle.setdefault(_type, 0)
				idle[_type] += 1
			else:
				idle.setdefault(_type, 0)
				idle[_type] = 0

	def cleanup(self):
		log.info("Cleanup")

		for dev in self.devidle.keys():
			if self.devidle[dev]["LEVEL"] > 0:
				ethcard(dev).set_max_speed()

	def update_tuning(self):
		load = self._load_monitor.get_load()
		for dev, devload in load.iteritems():
			self._updateIdle(dev, devload)
			print self.devidle
			if self.devidle[dev]["LEVEL"] == 0 and self.devidle[dev]["READ"] >= 6 and self.devidle[dev]["WRITE"] >= 6:
				self.devidle[dev]["LEVEL"] = 1

				log.info("%s: setting 100Mbps" % dev)
				ethcard(dev).set_speed(100)
			if self.devidle[dev]["LEVEL"] > 0 and (self.devidle[dev]["READ"] == 0 or self.devidle[dev]["WRITE"] == 0):
				self.devidle[dev]["LEVEL"] = 0

				log.info("%s: setting maximal speed" % dev)
				ethcard(dev).set_max_speed()
