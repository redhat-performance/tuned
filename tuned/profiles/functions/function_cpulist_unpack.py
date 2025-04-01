from . import base

class CPUListUnpack(base.Function):
	"""
	Unpacks a CPU list into a form with no ranges.

	====
	The following returns `1,2,3,5`:
	----
	${f:cpulist_unpack:1-3,5}
	----
	====
	"""
	def __init__(self):
		# arbitrary number of arguments
		super(CPUListUnpack, self).__init__("cpulist_unpack", 0)

	def execute(self, args):
		if not super(CPUListUnpack, self).execute(args):
			return None
		return ",".join(str(v) for v in self._cmd.cpulist_unpack(",,".join(args)))
