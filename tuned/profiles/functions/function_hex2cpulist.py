import os
import tuned.logs
import base
from tuned.utils.commands import commands

log = tuned.logs.get()

class hex2cpulist(base.Function):
	"""
	Conversion function: converts hexadecimal CPU mask to CPU list
	"""
	def __init__(self):
		# one argument
		super(self.__class__, self).__init__("hex2cpulist", 1)

	def execute(self, args):
		if not super(self.__class__, self).execute(args):
			return None
		return ",".join(str(v) for v in self._cmd.hex2cpulist(args[0]))
