import os
import tuned.logs
import base
from tuned.utils.commands import commands
from tuned.profiles.exceptions import InvalidProfileException

log = tuned.logs.get()

class assertion(base.Function):
	"""
	Assertion: compares argument 2 with argument 3. If they don't match
	it logs text from argument 1 and  throws InvalidProfileException. This
	exception will abort profile loading.
	"""
	def __init__(self):
		# 2 arguments
		super(self.__class__, self).__init__("assertion", 3)

	def execute(self, args):
		if not super(self.__class__, self).execute(args):
			return None
		if args[1] != args[2]:
			log.error("assertion '%s' failed: '%s' != '%s'" % (args[0], args[1], args[2]))
			raise InvalidProfileException("Assertion '%s' failed." % args[0])
		return None
