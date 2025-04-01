import os
import tuned.logs
from . import base
from tuned.utils.commands import commands

class kb2s(base.Function):
	"""
	Converts kilobytes to disk sectors.
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
