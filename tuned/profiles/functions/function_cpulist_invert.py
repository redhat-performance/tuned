import os
import tuned.logs
from . import base
from tuned.utils.commands import commands

log = tuned.logs.get()

class cpulist_invert(base.Function):
	"""
	Inverts a CPU list, i.e., returns its complement. The complement is
	computed from the list of online CPUs in `/sys/devices/system/cpu/online`.

	====
	On a system with 4 CPUs numbered from 0 to 3, the following will return `1`.
	----
	${f:cpulist_invert:0,2,3}
	----
	====
	"""
	def __init__(self):
		# arbitrary number of arguments
		super(cpulist_invert, self).__init__("cpulist_invert", 0)

	def execute(self, args):
		if not super(cpulist_invert, self).execute(args):
			return None
		return ",".join(str(v) for v in self._cmd.cpulist_invert(",,".join(args)))
