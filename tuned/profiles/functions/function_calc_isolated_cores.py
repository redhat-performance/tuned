import os
import glob
import tuned.logs
from . import base
import tuned.consts as consts

log = tuned.logs.get()

class calc_isolated_cores(base.Function):
	"""
	Calculates and returns a list of isolated cores. The argument
	specifies how many cores per socket should be reserved for housekeeping.
	If not specified, a single core is reserved per socket and the rest is isolated.

	====
	Reserve two cores per socket for housekeeping and return the list of remaining cores:
	----
	${f:calc_isolated_cores:2}
	----
	====
	"""
	def __init__(self):
		# max 1 argument
		super(calc_isolated_cores, self).__init__("calc_isolated_cores", 1)

	def execute(self, args):
		if not super(calc_isolated_cores, self).execute(args):
			return None
		cpus_reserve = 1
		if len(args) > 0:
			if not args[0].isdecimal() or int(args[0]) < 0:
				log.error("invalid argument '%s' for builtin function '%s', it must be non-negative integer" %
					(args[0], self._name))
				return None
			else:
				cpus_reserve = int(args[0])

		topo = {}
		for cpu in glob.iglob(os.path.join(consts.SYSFS_CPUS_PATH, "cpu*")):
			cpuid = os.path.basename(cpu)[3:]
			if cpuid.isdecimal():
				physical_package_id = os.path.join(cpu, "topology/physical_package_id")
				# Show no errors when the physical_package_id file does not exist -- the CPU may be offline.
				if not os.path.exists(physical_package_id):
					log.debug("file '%s' does not exist, cpu%s offline?" % (physical_package_id, cpuid))
					continue
				socket = self._cmd.read_file(physical_package_id).strip()
				if socket.isdecimal():
					topo[socket] = topo.get(socket, []) + [cpuid]

		isol_cpus = []
		for cpus in topo.values():
			cpus.sort(key = int)
			isol_cpus = isol_cpus + cpus[cpus_reserve:]
		isol_cpus.sort(key = int)
		return ",".join(isol_cpus)
