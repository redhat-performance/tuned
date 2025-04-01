import os
import fnmatch

from . import base
from tuned.utils.commands import commands
from tuned import logs

log = logs.get()
cmd = commands()

SYSFS_DIR = "/sys/devices/system/cpu/intel_uncore_frequency/"

class Package2Uncores(base.Function):
	"""
	Returns a comma-separated list of uncore devices for a package (socket).
	Multiple socket numbers can be specified in separate arguments.

	====
	On a system with a single socket and a single die,
	the following will return `package_00_die_00`:
	----
	${f:package2uncores:0}
	----
	====
	"""

	def __init__(self):
		super(Package2Uncores, self).__init__("package2uncores", 0)

	def execute(self, args):
		if not super(Package2Uncores, self).execute(args):
			return None

		if len(args) <= 0:
			return None

		try:
			all_uncores = os.listdir(SYSFS_DIR)
		except OSError:
			return None

		# For new TPMI interface use only uncore devices
		tpmi_devices = fnmatch.filter(all_uncores, 'uncore*')
		if len(tpmi_devices) > 0:
			is_tpmi = True
			all_uncores = tpmi_devices
		else:
			is_tpmi = False

		devices = []

		for uncore in all_uncores:
			if is_tpmi:
				f = SYSFS_DIR + uncore + "/package_id"
				if not os.path.exists(f):
					log.warning("File '%s' does not exist" % f)
					continue

				value = cmd.read_file(f)
			else:
				# uncore string is in form: package_NN_die_MM, do not expect more than 99 packages
				value = uncore[8:10]

			try:
				package_id = int(value)
			except ValueError:
				log.warning("Invalid package id '%s' for uncore '%s'" % (value, uncore))
				continue

			for package_pattern in args:
				try:
					this_package_id = int(package_pattern)
				except ValueError:
					if fnmatch.fnmatch(value, package_pattern):
						devices.append(uncore)
				else:
					if package_id == this_package_id:
						devices.append(uncore)

		return ",".join(devices) if len(devices) > 0 else None
