import os
import tuned.logs
from . import base
from tuned.utils.commands import commands

log = tuned.logs.get()

class cpulist2hex(base.Function):
	"""
	Converts a CPU list into a hexadecimal CPU mask.

	====
	The following will return `00000007`.
	----
	${f:cpulist2hex:0-3}
	----
	====
	"""
	def __init__(self):
		# arbitrary number of arguments
		super(cpulist2hex, self).__init__("cpulist2hex", 0)

	def execute(self, args):
		if not super(cpulist2hex, self).execute(args):
			return None
		return self._cmd.cpulist2hex(",,".join(args))
