import os
import tuned.logs
from . import base
from tuned.utils.commands import commands

log = tuned.logs.get()

class cpulist_online(base.Function):
	"""
	Checks whether CPUs from list are online, returns list containing
	only online CPUs
	"""
	def __init__(self):
		# arbitrary number of arguments
		super(cpulist_online, self).__init__("cpulist_online", 0)

	def execute(self, args):
		if not super(cpulist_online, self).execute(args):
			return None
		cpus = self._cmd.cpulist_unpack(",".join(args))
		online = self._cmd.cpulist_unpack(self._cmd.read_file("/sys/devices/system/cpu/online"))
		return ",".join(str(v) for v in set(cpus).intersection(set(online)))
