import os
import tuned.logs
from . import base
from tuned.utils.commands import commands

log = tuned.logs.get()

class hex2cpulist(base.Function):
	"""
	Converts a hexadecimal CPU mask into a CPU list.

	====
	The following will return `0,1,2,3`:
	----
	${f:hex2cpulist:00000007}
	----
	====
	"""
	def __init__(self):
		# 1 argument
		super(hex2cpulist, self).__init__("hex2cpulist", 1, 1)

	def execute(self, args):
		if not super(hex2cpulist, self).execute(args):
			return None
		return ",".join(str(v) for v in self._cmd.hex2cpulist(args[0]))
