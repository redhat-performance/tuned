import tuned.logs
from . import base

log = tuned.logs.get()

class CPUList2Devs(base.Function):
	"""
	Converts a CPU list into a comma-separated list of device names.

	====
	The following will return `cpu1,cpu2,cpu3,cpu5`:
	----
	${f:cpulist2devs:1-3,5}
	----
	====
	"""
	def __init__(self):
		# arbitrary number of arguments
		super(CPUList2Devs, self).__init__("cpulist2devs", 0)

	def execute(self, args):
		if not super(CPUList2Devs, self).execute(args):
			return None
		return self._cmd.cpulist2string(self._cmd.cpulist_unpack(",".join(args)), prefix = "cpu")
