import os
import tuned.logs
from . import base
from tuned.utils.commands import commands
from tuned.profiles.exceptions import InvalidProfileException

log = tuned.logs.get()

class assertion_non_equal(base.Function):
	"""
	Assertion non equal: compares argument 2 with argument 3. If they match
	it logs text from argument 1 and  throws InvalidProfileException. This
	exception will abort profile loading.
	"""
	def __init__(self):
		# 2 arguments
		super(assertion_non_equal, self).__init__("assertion_non_equal", 3)

	def execute(self, args):
		if not super(assertion_non_equal, self).execute(args):
			return None
		if args[1] == args[2]:
			log.error("assertion '%s' failed: '%s' == '%s'" % (args[0], args[1], args[2]))
			raise InvalidProfileException("Assertion '%s' failed." % args[0])
		return None
