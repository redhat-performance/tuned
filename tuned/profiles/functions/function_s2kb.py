import os
import tuned.logs
from . import base
from tuned.utils.commands import commands

class S2KB(base.Function):
	"""
	Converts disk sectors to kilobytes.
	"""
	def __init__(self):
		# 1 argument
		super(S2KB, self).__init__("s2kb", 1, 1)

	def execute(self, args):
		if not super(S2KB, self).execute(args):
			return None
		try:
			return str(int(round(int(args[0]) / 2)))
		except ValueError:
			return None
