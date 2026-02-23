import os
import tuned.logs
from tuned.utils.commands import commands

log = tuned.logs.get()

class Function(object):
	"""
	Built-in function
	"""
	def __init__(self, nargs_max, nargs_min = None):
		self._nargs_max = nargs_max
		self._nargs_min = nargs_min
		self._cmd = commands()

	@property
	def name(self):
		return self.__class__.__module__.split(".")[-1].split("_", 1)[1]

	# checks arguments
	# nargs_max - maximal number of arguments, there mustn't be more arguments,
	#             if nargs_max is 0, number of arguments is unlimited
	# nargs_min - minimal number of arguments, if not None there must
	#             be the same number of arguments or more
	@classmethod
	def _check_args(cls, args, nargs_max, nargs_min = None):
		if args is None or nargs_max is None:
			return False
		la = len(args)
		return (nargs_max == 0 or nargs_max >= la) and (nargs_min is None or nargs_min <= la)

	def execute(self, args):
		if self._check_args(args, self._nargs_max, self._nargs_min):
			return True
		else:
			log.error("invalid number of arguments for builtin function '%s'" % self.name)
		return False
