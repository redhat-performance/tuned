import tuned.monitors
import os
import re
from tuned.utils.nettool import ethcard

class NetMonitor(tuned.monitors.Monitor):

	@classmethod
	def _init_available_devices(cls):
		available = []
		for root, dirs, files in os.walk("/sys/devices"):
			if root.endswith("/net") and not root.endswith("/virtual/net"):
				available += dirs
		
		cls._available_devices = set(available)

		for dev in available:
			max_speed = cls._calcspeed(ethcard(dev).get_max_speed())
			cls._load[dev] = {}
			cls._load[dev]["new"] = ['0', '0', '0', '0']
			cls._load[dev]["max"] = [max_speed, 1, max_speed, 1]
			cls._updateStat(dev)
			cls._load[dev]["max"] = [max_speed, 1, max_speed, 1]

	@classmethod
	def _calcspeed(cls, speed):
		# 0.6 is just a magical constant (empirical value): Typical workload on netcard won't exceed
		# that and if it does, then the code is smart enough to adapt it.
		# 1024 * 1024 as for MB -> B
		# speed / 8  Mb -> MB
		return (int) (0.6 * 1024 * 1024 * speed / 8)

	@classmethod
	def _calcdiff(cls, dev):
		l = []
		for i in xrange(len(cls._load[dev]["old"])):
			l.append(int(cls._load[dev]["new"][i]) - int(cls._load[dev]["old"][i]))
		return l

	@classmethod
	def _updateStat(cls, dev):
		cls._load[dev]["old"] = cls._load[dev]["new"][:]
		l = open("/sys/class/net/"+dev+"/statistics/rx_bytes", "r").read().strip()
		cls._load[dev]["new"][0] = l
		l = open("/sys/class/net/"+dev+"/statistics/rx_packets", "r").read().strip()
		cls._load[dev]["new"][1] = l
		l = open("/sys/class/net/"+dev+"/statistics/tx_bytes", "r").read().strip()
		cls._load[dev]["new"][2] = l
		l = open("/sys/class/net/"+dev+"/statistics/tx_packets", "r").read().strip()
		cls._load[dev]["new"][3] = l
		l = cls._calcdiff(dev)
		for i in xrange(len(l)):
			if l[i] > cls._load[dev]["max"][i]:
				cls._load[dev]["max"][i] = l[i]
		cls._load[dev]["diff"] = cls._calcdiff(dev)

		cls._load[dev]["READ"] = float(cls._load[dev]["diff"][0]) / float(cls._load[dev]["max"][0])
		cls._load[dev]["WRITE"] = float(cls._load[dev]["diff"][2]) / float(cls._load[dev]["max"][2])

	@classmethod
	def update(cls):
		for device in cls._updating_devices:
			cls._updateStat(device)

