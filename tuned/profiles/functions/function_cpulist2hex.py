import os
import tuned.logs
import base
from tuned.utils.commands import commands

log = tuned.logs.get()

class cpulist2hex(base.Function):
	"""
	Conversion function: converts CPU list to hexadecimal CPU mask
	"""
	def __init__(self):
		# arbitrary number of arguments
		super(self.__class__, self).__init__("cpulist2hex", 0)

	def execute(self, args):
		if not super(self.__class__, self).execute(args):
			return None
		return self._cmd.cpulist2hex(",,".join(args))
