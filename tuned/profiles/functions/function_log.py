import tuned.logs
from . import base

log = tuned.logs.get()

class execute(base.Function):
	"""
	Expands to concatenation of arguments and logs the result, useful for debugging.
	"""
	def __init__(self):
		# unlimited number of arguments, min 1 argument (the value to log)
		super(execute, self).__init__("log", 0, 1)

	def execute(self, args):
		if not super(execute, self).execute(args):
			return None
		s = "".join(args)
		log.info(s)
		return s
