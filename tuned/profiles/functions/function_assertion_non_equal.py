import os
import tuned.logs
from . import base
from tuned.utils.commands import commands
from tuned.profiles.exceptions import InvalidProfileException

log = tuned.logs.get()

class assertion_non_equal(base.Function):
	"""
	Compares the second argument and the third argument.
	If they _match_, the function logs the text from
	the first argument as an error and aborts profile loading.

	====
	The following will pass without errors:
	----
	${f:assertion_non_equal:fatal error:3:5}
	----
	====
	"""
	def __init__(self):
		# 3 arguments
		super(assertion_non_equal, self).__init__("assertion_non_equal", 3, 3)

	def execute(self, args):
		if not super(assertion_non_equal, self).execute(args):
			return None
		if args[1] == args[2]:
			log.error("assertion '%s' failed: '%s' == '%s'" % (args[0], args[1], args[2]))
			raise InvalidProfileException("Assertion '%s' failed." % args[0])
		return None
