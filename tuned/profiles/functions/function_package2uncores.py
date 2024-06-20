import os
import fnmatch

from . import base
from tuned.utils.commands import commands

cmd = commands()

SYSFS_DIR = "/sys/devices/system/cpu/intel_uncore_frequency/"

class package2uncores(base.Function):
	"""
	Provides uncore device list for a package (socket)
	"""

	def __init__(self):
		# 1 argument
		super(package2uncores, self).__init__("package2uncores", 1, 1)

	def execute(self, args):
		if not super(package2uncores, self).execute(args):
			return None

		if len(args) <= 0:
			return None

		package_pattern = args[0]

		try:
			this_package_id = int(package_pattern)
			do_fnmatch = False
		except ValueError:
			do_fnmatch = True

		all_uncores = os.listdir(SYSFS_DIR)
		is_tpmi = False

		# For new TPMI interface use only uncore devices
		tpmi_devices = fnmatch.filter(all_uncores, 'uncore*')
		if len(tpmi_devices) > 0:
			is_tpmi = True
			all_uncores = tpmi_devices

		devices = []

		for uncore in all_uncores:
			if is_tpmi:
				f = SYSFS_DIR + uncore + "/package_id"
				if not os.path.exists(f):
					continue

				value = cmd.read_file(f)
				if len(value) == 0:
					continue
			else:
				# uncore string is in form package_NN_die_MM
				# TODO make this more reliable?
				value = uncore[8:10]

			try:
				package_id = int(value)
			except ValueError:
				continue

			if do_fnmatch:
				if fnmatch.fnmatch(package_id, package_pattern):
					devices.append(uncore)
			else:
				if package_id == this_package_id:
					devices.append(uncore)

		return ",".join(devices) if len(devices) > 0 else None
