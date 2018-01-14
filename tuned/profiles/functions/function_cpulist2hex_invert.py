import os
import tuned.logs
from . import base
from tuned.utils.commands import commands

log = tuned.logs.get()

class cpulist2hex_invert(base.Function):
	"""
	Converts CPU list to hexadecimal CPU mask and inverts it
	"""
	def __init__(self):
		# arbitrary number of arguments
		super(cpulist2hex_invert, self).__init__("cpulist2hex_invert", 0)

	def execute(self, args):
		if not super(cpulist2hex_invert, self).execute(args):
			return None
		# current implementation inverts the CPU list and then converts it to hexmask
		return self._cmd.cpulist2hex(",".join(str(v) for v in self._cmd.cpulist_invert(",,".join(args))))
