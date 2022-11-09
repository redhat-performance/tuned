import tuned.logs
from . import base

log = tuned.logs.get()

class cpulist2devs(base.Function):
	"""
	Conversion function: converts CPU list to device strings
	"""
	def __init__(self):
		# arbitrary number of arguments
		super(cpulist2devs, self).__init__("cpulist2devs", 0)

	def execute(self, args):
		if not super(cpulist2devs, self).execute(args):
			return None
		return self._cmd.cpulist2string(self._cmd.cpulist_unpack(",".join(args)), prefix = "cpu")
