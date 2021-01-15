from tuned.profiles.functions import base

class kb2s(base.Function):
	"""
	Conversion function: kbytes to sectors
	"""
	def __init__(self):
		# 1 argument
		super(kb2s, self).__init__("kb2s", 1, 1)

	def execute(self, args):
		if not super(kb2s, self).execute(args):
			return None
		try:
			return str(int(args[0]) * 2)
		except ValueError:
			return None
