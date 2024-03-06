import os
import fnmatch

from . import base
from tuned.utils.commands import commands

cmd = commands()

SYSFS_DIR = "/sys/devices/system/cpu/"

class package2cpus(base.Function):
	"""
	Provides cpu device list for a package (socket)
	"""

	def __init__(self):
		# 1 argument
		super(package2cpus, self).__init__("package2cpus", 1, 1)

	def execute(self, args):
		if not super(package2cpus, self).execute(args):
			return None

		if len(args) <= 0:
			return None

		package_pattern = args[0]

		try:
			this_package_id = int(package_pattern)
			do_fnmatch = False
		except ValueError:
			do_fnmatch = True

		all_cpus = fnmatch.filter(os.listdir(SYSFS_DIR), "cpu[0-9]*")
		devices = []

		for cpu in all_cpus:
			f = SYSFS_DIR + cpu + "/topology/physical_package_id"
			if not os.path.exists(f):
				continue

			value = cmd.read_file(f)
			if len(value) == 0:
				continue

			try:
				package_id = int(value)
			except ValueError:
				continue

			if do_fnmatch:
				if fnmatch.fnmatch(value, package_pattern):
					devices.append(cpu)
			else:
				if package_id == this_package_id:
					devices.append(cpu)

		return ",".join(devices) if len(devices) > 0 else None
