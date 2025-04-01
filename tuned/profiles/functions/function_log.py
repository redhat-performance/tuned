import tuned.logs
from . import base

log = tuned.logs.get()

class Log(base.Function):
	"""
	Returns the concatenation of its arguments and also logs the return value,
	which is useful for debugging.

	.Using `log` to debug intermediate values
	====
	Since the arguments of `log` "fall through" the function, it
	can be used as below for debugging intermediate values:
	----
	[variables]
	isolated_cores_hex = ${f:cpulist2hex:${f:log:${f:calc_isolated_cores}}}
	----
	====
	"""
	def __init__(self):
		# unlimited number of arguments, min 1 argument (the value to log)
		super(Log, self).__init__("log", 0, 1)

	def execute(self, args):
		if not super(Log, self).execute(args):
			return None
		s = "".join(args)
		log.info(s)
		return s
