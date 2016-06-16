import os
import tuned.logs
import base
from tuned.utils.commands import commands

class execute(base.Function):
	"""
	Executes process and substitutes its output.
	"""
	def __init__(self):
		# unlimited number of arguments, min 1 argument (the name of executable)
		super(self.__class__, self).__init__("exec", 0, 1)

	def execute(self, args):
		if not super(self.__class__, self).execute(args):
			return None
		(ret, out) = self._cmd.execute(args)
		if ret == 0:
			return out
		return None
