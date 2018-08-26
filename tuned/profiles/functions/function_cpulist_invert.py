import os
import tuned.logs
from . import base
from tuned.utils.commands import commands

log = tuned.logs.get()

class cpulist_invert(base.Function):
	"""
	Inverts list of CPUs (makes its complement). For the complement it
	gets number of online CPUs from the /sys/devices/system/cpu/online,
	e.g. system with 4 CPUs (0-3), the inversion of list "0,2,3" will be
	"1"
	"""
	def __init__(self):
		# arbitrary number of arguments
		super(cpulist_invert, self).__init__("cpulist_invert", 0)

	def execute(self, args):
		if not super(cpulist_invert, self).execute(args):
			return None
		return ",".join(str(v) for v in self._cmd.cpulist_invert(",,".join(args)))
