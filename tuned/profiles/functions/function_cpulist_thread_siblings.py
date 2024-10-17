import tuned.logs
from . import base

log = tuned.logs.get()

class cpulist_thread_siblings(base.Function):
	"""
	Returns the thread siblings (a.k.a Hyperthreads) of the
	given CPUs. Never returns any CPUs from the given list.
	"""
	def __init__(self):
		# arbitrary number of arguments
		super(cpulist_thread_siblings, self).__init__("cpulist_thread_siblings", 0)

	def execute(self, args):
		if not super(cpulist_thread_siblings, self).execute(args):
			return None
		cpus = set(self._cmd.cpulist_unpack(",".join(args)))
		all_siblings = set()
		for cpu in cpus:
			siblings = self._cmd.read_file("/sys/devices/system/cpu/cpu%d/topology/thread_siblings_list" % cpu).strip()
			all_siblings |= set(self._cmd.cpulist_unpack(siblings))
		return ",".join(str(v) for v in list(all_siblings - cpus))
