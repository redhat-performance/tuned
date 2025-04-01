import os
import tuned.logs
from . import base
from tuned.utils.commands import commands

log = tuned.logs.get()

class CPUListPresent(base.Function):
	"""
	Checks whether the CPUs from a given CPU list are present on the system.
	Returns a CPU list containing only the present CPUs from the given list.
	"""
	def __init__(self):
		# arbitrary number of arguments
		super(CPUListPresent, self).__init__("cpulist_present", 0)

	def execute(self, args):
		if not super(CPUListPresent, self).execute(args):
			return None
		cpus = self._cmd.cpulist_unpack(",,".join(args))
		present = self._cmd.cpulist_unpack(self._cmd.read_file("/sys/devices/system/cpu/present"))
		return ",".join(str(v) for v in sorted(list(set(cpus).intersection(set(present)))))
