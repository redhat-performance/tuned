from . import base

class KB2S(base.Function):
	"""
	Converts kilobytes to disk sectors.
	"""
	def __init__(self):
		# 1 argument
		super(KB2S, self).__init__(1, 1)

	def execute(self, args):
		if not super(KB2S, self).execute(args):
			return None
		try:
			return str(int(args[0]) * 2)
		except ValueError:
			return None
