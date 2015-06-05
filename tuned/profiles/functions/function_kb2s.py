import os
import tuned.logs
import base
from tuned.utils.commands import commands

class kb2s(base.Function):
	"""
	Conversion function: kbytes to sectors
	"""
	def __init__(self):
		# one argument
		super(self.__class__, self).__init__("kb2s", 1)

	def execute(self, args):
		if not super(self.__class__, self).execute(args):
			return None
		try:
			return str(int(args[0]) * 2)
		except ValueError:
			return None
