import tuned.logs
from . import base

log = tuned.logs.get()

class CheckNetQueueCount(base.Function):
	"""
	Checks whether the first argument is a valid queue count for net devices.
	If yes, returns it, otherwise returns the number of housekeeping CPUs.
	"""
	def __init__(self):
		# 1 argument
		super(CheckNetQueueCount, self).__init__(1, 1)

	def execute(self, args):
		if not super(CheckNetQueueCount, self).execute(args):
			return None
		if args[0].isdigit():
			return args[0]
		(ret, out) = self._cmd.execute(["nproc"])
		log.warning("net-dev queue count is not correctly specified, setting it to HK CPUs %s" % (out))
		return out
