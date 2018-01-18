import os
import tuned.logs
from . import base
from tuned.utils.commands import commands

log = tuned.logs.get()

class cpulist_present(base.Function):
	"""
	Checks whether CPUs from list are present, returns list containing
	only present CPUs
	"""
	def __init__(self):
		# arbitrary number of arguments
		super(cpulist_present, self).__init__("cpulist_present", 0)

	def execute(self, args):
		if not super(cpulist_present, self).execute(args):
			return None
		cpus = self._cmd.cpulist_unpack(",,".join(args))
		present = self._cmd.cpulist_unpack(self._cmd.read_file("/sys/devices/system/cpu/present"))
		return ",".join(str(v) for v in sorted(list(set(cpus).intersection(set(present)))))
