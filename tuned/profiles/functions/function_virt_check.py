import os
import tuned.logs
from . import base
from tuned.utils.commands import commands

class virt_check(base.Function):
	"""
	Checks whether running inside virtual machine (VM) or on bare metal.
	If running inside VM expands to argument 1, otherwise expands to
	argument 2 (even on error).
	"""
	def __init__(self):
		# 2 arguments
		super(virt_check, self).__init__("virt_check", 2)

	def execute(self, args):
		if not super(virt_check, self).execute(args):
			return None
		(ret, out) = self._cmd.execute(["virt-what"])
		if ret == 0 and len(out) > 0:
			return args[0]
		return args[1]
