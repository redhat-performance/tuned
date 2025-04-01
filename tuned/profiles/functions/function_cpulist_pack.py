import os
import tuned.logs
from . import base
from tuned.utils.commands import commands

log = tuned.logs.get()

class CPUListPack(base.Function):
	"""
	Packs a CPU list into the most succint form.

	====
	The following returns `1-3,5`:
	----
	${f:cpulist_pack:1,2,3,5}
	----
	====
	"""
	def __init__(self):
		# arbitrary number of arguments
		super(CPUListPack, self).__init__("cpulist_pack", 0)

	def execute(self, args):
		if not super(CPUListPack, self).execute(args):
			return None
		return ",".join(str(v) for v in self._cmd.cpulist_pack(",,".join(args)))
