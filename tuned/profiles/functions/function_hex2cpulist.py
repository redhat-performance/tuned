from . import base

class Hex2CPUList(base.Function):
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
		super(Hex2CPUList, self).__init__("hex2cpulist", 1, 1)

	def execute(self, args):
		if not super(Hex2CPUList, self).execute(args):
			return None
		return ",".join(str(v) for v in self._cmd.hex2cpulist(args[0]))
