import tuned.monitors
import os
import re
from tuned.utils.nettool import ethcard
from tuned.utils.commands import commands

cmd = commands()

class NetMonitor(tuned.monitors.Monitor):

	@classmethod
	def _init_available_devices(cls):
		available = []
		for root, dirs, files in os.walk("/sys/devices"):
			if root.endswith("/net") and not root.endswith("/virtual/net"):
				available += dirs
		
		cls._available_devices = set(available)

		for dev in available:
			#max_speed = cls._calcspeed(ethcard(dev).get_max_speed())
			cls._load[dev] = ['0', '0', '0', '0']

	@classmethod
	def _calcspeed(cls, speed):
		# 0.6 is just a magical constant (empirical value): Typical workload on netcard won't exceed
		# that and if it does, then the code is smart enough to adapt it.
		# 1024 * 1024 as for MB -> B
		# speed / 8  Mb -> MB
		return (int) (0.6 * 1024 * 1024 * speed / 8)

	@classmethod
	def _updateStat(cls, dev):
		files = ["rx_bytes", "rx_packets", "tx_bytes", "tx_packets"]
		for i,f in enumerate(files):
			cls._load[dev][i] = cmd.read_file("/sys/class/net/" + dev + "/statistics/" + f, err_ret = "0").strip()

	@classmethod
	def update(cls):
		for device in cls._updating_devices:
			cls._updateStat(device)

