import os
import tuned.logs
from . import base
from tuned.utils.commands import commands

log = tuned.logs.get()

class cpulist_pack(base.Function):
	"""
	Conversion function: packs CPU list in form 1,2,3,5 to 1-3,5.
	The cpulist_unpack is used as a preprocessor, so it always returns
	optimal results. For details about input syntax see cpulist_unpack.
	"""
	def __init__(self):
		# arbitrary number of arguments
		super(cpulist_pack, self).__init__("cpulist_pack", 0)

	def execute(self, args):
		if not super(cpulist_pack, self).execute(args):
			return None
		return ",".join(str(v) for v in self._cmd.cpulist_pack(",,".join(args)))
