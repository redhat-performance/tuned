import tuned.logs
from . import base

log = tuned.logs.get()

class check_net_queue_count(base.Function):
	"""
	Checks whether the user has specified a queue count for net devices. If
        not, return the number of housekeeping CPUs.
	"""
	def __init__(self):
		# 1 argument
		super(check_net_queue_count, self).__init__("check_net_queue_count", 1, 1)

	def execute(self, args):
		if not super(check_net_queue_count, self).execute(args):
			return None
		if args[0].isdigit():
			return args[0]
		# Check for none to get rid of WARN log
		if args[0].lower() == "none":
			return None
		(ret, out) = self._cmd.execute(["nproc"])
		log.warn("net-dev queue count is not correctly specified, setting it to HK CPUs %s" % (out))
		return out
