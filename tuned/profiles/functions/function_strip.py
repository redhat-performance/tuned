import os
import tuned.logs
from . import base
from tuned.utils.commands import commands

class strip(base.Function):
	"""
	Makes string from all arguments and strip it
	"""
	def __init__(self):
		# unlimited number of arguments, min 1 argument
		super(strip, self).__init__("strip", 0, 1)

	def execute(self, args):
		if not super(strip, self).execute(args):
			return None
		return "".join(args).strip()
