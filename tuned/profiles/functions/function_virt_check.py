import os
import tuned.logs
from . import base
from tuned.utils.commands import commands

class virt_check(base.Function):
	"""
	Checks whether *TuneD* is running inside a virtual machine (VM) or on bare metal.

	Inside a VM, it returns the first argument.
	Otherwise returns the second argument (even on error).

	====
	The following returns `VM` when running in a virtual machine:
	----
	${f:virt_check:VM:Bare}
	----
	====
	"""
	def __init__(self):
		# 2 arguments
		super(virt_check, self).__init__("virt_check", 2, 2)

	def execute(self, args):
		if not super(virt_check, self).execute(args):
			return None
		(ret, out) = self._cmd.execute(["virt-what"])
		if ret == 0 and len(out) > 0:
			return args[0]
		return args[1]
