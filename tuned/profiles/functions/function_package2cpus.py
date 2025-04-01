import os
import fnmatch

from . import base
from tuned.utils.commands import commands
from tuned import logs

log = logs.get()
cmd = commands()

SYSFS_DIR = "/sys/devices/system/cpu/"

class Package2CPUs(base.Function):
	"""
	Returns a comma-separated list of CPU devices for a package (socket).
	Multiple socket numbers can be specified in separate arguments.

	====
	On a system with two CPU sockets, both with 4 cores, the
	following will return `cpu0,cpu1,cpu2,cpu3,cpu4,cpu5,cpu6,cpu7`:
	----
	${f:package2cpus:0:1}
	----
	====
	"""

	def __init__(self):
		super(Package2CPUs, self).__init__("package2cpus", 0)

	def execute(self, args):
		if not super(Package2CPUs, self).execute(args):
			return None

		if len(args) <= 0:
			return None

		try:
			all_cpus = fnmatch.filter(os.listdir(SYSFS_DIR), "cpu[0-9]*")
		except OSError:
			return None

		devices = []

		for cpu in all_cpus:
			f = SYSFS_DIR + cpu + "/topology/physical_package_id"
			if not os.path.exists(f):
				log.warning("File '%s' does not exist" % f)
				continue

			value = cmd.read_file(f)

			try:
				package_id = int(value)
			except ValueError:
				log.warning("Invalid package id '%s' for cpu '%s'" % (value, cpu))
				continue

			for package_pattern in args:
				try:
					this_package_id = int(package_pattern)
				except ValueError:
					if fnmatch.fnmatch(value, package_pattern):
						devices.append(cpu)
				else:
					if package_id == this_package_id:
						devices.append(cpu)

		return ",".join(devices) if len(devices) > 0 else None
