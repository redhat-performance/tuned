from . import base

class CPUList2Hex(base.Function):
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
		super(CPUList2Hex, self).__init__("cpulist2hex", 0)

	def execute(self, args):
		if not super(CPUList2Hex, self).execute(args):
			return None
		return self._cmd.cpulist2hex(",,".join(args))
