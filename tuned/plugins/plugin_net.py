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
		self.stats = {}
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

	def _calc_speed(self, speed):
		# 0.6 is just a magical constant (empirical value): Typical workload on netcard won't exceed
		# that and if it does, then the code is smart enough to adapt it.
		# 1024 * 1024 as for MB -> B
		# speed / 8  Mb -> MB
		return (int) (0.6 * 1024 * 1024 * speed / 8)

	def _calc_diff(self, dev):
		l = []
		for i in xrange(len(self.stats[dev]["old"])):
			l.append(int(self.stats[dev]["new"][i]) - int(self.stats[dev]["old"][i]))
		return l

	def _update_idle(self, dev):
		idle = self.devidle.setdefault(dev, {})
		idle.setdefault("LEVEL", 0)
		for _type in ("read", "write"):
			if self.stats[dev][_type] <= 0.05:
				idle.setdefault(_type, 0)
				idle[_type] += 1
			else:
				idle.setdefault(_type, 0)
				idle[_type] = 0

	def _init_stats(self, dev):
		if not self.stats.has_key(dev):
			max_speed = self._calc_speed(ethcard(dev).get_max_speed())
			self.stats[dev] = {}
			self.stats[dev]["new"] = ['0', '0', '0', '0']
			self.stats[dev]["max"] = [max_speed, 1, max_speed, 1]
			self.stats[dev]["max"] = [max_speed, 1, max_speed, 1]

	def _update_stats(self, dev, devload):
		self.stats[dev]["old"] = list(self.stats[dev]["new"])
		self.stats[dev]["new"] = list(devload)
		l = self._calc_diff(dev)
		for i in xrange(len(l)):
			if l[i] > self.stats[dev]["max"][i]:
				self.stats[dev]["max"][i] = l[i]

		self.stats[dev]["diff"] = l
	
		self.stats[dev]["read"] = float(self.stats[dev]["diff"][0]) / float(self.stats[dev]["max"][0])
		self.stats[dev]["write"] = float(self.stats[dev]["diff"][2]) / float(self.stats[dev]["max"][2])

	def cleanup(self):
		log.info("Cleanup")

		for dev in self.devidle.keys():
			if self.devidle[dev]["LEVEL"] > 0:
				ethcard(dev).set_max_speed()

	def update_tuning(self):
		load = self._load_monitor.get_load()
		for dev, devload in load.iteritems():
			self._init_stats(dev)
			self._update_stats(dev, devload)
			self._update_idle(dev)

			if self.devidle[dev]["LEVEL"] == 0 and self.devidle[dev]["read"] >= 6 and self.devidle[dev]["write"] >= 6:
				self.devidle[dev]["LEVEL"] = 1

				log.info("%s: setting 100Mbps" % dev)
				ethcard(dev).set_speed(100)
			if self.devidle[dev]["LEVEL"] > 0 and (self.devidle[dev]["read"] == 0 or self.devidle[dev]["write"] == 0):
				self.devidle[dev]["LEVEL"] = 0

				log.info("%s: setting maximal speed" % dev)
				ethcard(dev).set_max_speed()

			log.debug("%s load: read %f, write %f" % (dev, self.stats[dev]["read"], self.stats[dev]["write"]))
			log.debug("%s idle: read %d, write %d, level %d" % (dev, self.devidle[dev]["read"], self.devidle[dev]["write"], self.devidle[dev]["LEVEL"]))
