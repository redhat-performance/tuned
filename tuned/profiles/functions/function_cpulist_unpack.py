import os
import tuned.logs
import base
from tuned.utils.commands import commands

log = tuned.logs.get()

class cpulist_unpack(base.Function):
	"""
	Conversion function: unpacks CPU list in form 1-3,4 to 1,2,3,4
	"""
	def __init__(self):
		# arbitrary number of arguments
		super(self.__class__, self).__init__("cpulist_unpack", 0)

	def execute(self, args):
		if not super(self.__class__, self).execute(args):
			return None
		return ",".join(str(v) for v in self._cmd.cpulist_unpack(",,".join(args)))
