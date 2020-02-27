from tuned.profiles.functions import base

class cpulist2hex(base.Function):
	"""
	Conversion function: converts CPU list to hexadecimal CPU mask
	"""
	def __init__(self):
		# arbitrary number of arguments
		super(cpulist2hex, self).__init__("cpulist2hex", 0)

	def execute(self, args):
		if not super(cpulist2hex, self).execute(args):
			return None
		return self._cmd.cpulist2hex(",,".join(args))
