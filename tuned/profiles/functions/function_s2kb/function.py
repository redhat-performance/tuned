from tuned.profiles.functions import base

class s2kb(base.Function):
	"""
	Conversion function: sectors to kbytes
	"""
	def __init__(self):
		# 1 argument
		super(s2kb, self).__init__("s2kb", 1, 1)

	def execute(self, args):
		if not super(s2kb, self).execute(args):
			return None
		try:
			return str(int(round(int(args[0]) / 2)))
		except ValueError:
			return None
