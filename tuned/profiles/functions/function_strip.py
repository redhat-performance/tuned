import os
import tuned.logs
from . import base
from tuned.utils.commands import commands

class Strip(base.Function):
	"""
	Creates a string by concatenating all arguments,
	stripping any leading or trailing whitespace from
	the result.

	====
	The following returns `foo bar`:
	----
	${f:strip:  foo :bar  }
	----
	====
	"""
	def __init__(self):
		# unlimited number of arguments, min 1 argument
		super(Strip, self).__init__("strip", 0, 1)

	def execute(self, args):
		if not super(Strip, self).execute(args):
			return None
		return "".join(args).strip()
