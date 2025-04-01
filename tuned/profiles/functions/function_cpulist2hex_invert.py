from . import base

class CPUList2HexInvert(base.Function):
	"""
	Converts a CPU list into a hexadecimal CPU mask and inverts it.

	====
	On a system with 4 CPUs numbered from 0 to 3, the following will
	return `00000002`, because only CPU1 is in the complement.
	----
	${f:cpulist2hex_invert:0,2,3}
	----
	====
	"""
	def __init__(self):
		# arbitrary number of arguments
		super(CPUList2HexInvert, self).__init__(0)

	def execute(self, args):
		if not super(CPUList2HexInvert, self).execute(args):
			return None
		# current implementation inverts the CPU list and then converts it to hexmask
		return self._cmd.cpulist2hex(",".join(str(v) for v in self._cmd.cpulist_invert(",,".join(args))))
