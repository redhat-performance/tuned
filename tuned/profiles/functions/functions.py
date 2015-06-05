import os
import re
import glob
import repository
import tuned.logs
import tuned.consts as consts
from tuned.utils.commands import commands

log = tuned.logs.get()

cmd = commands()

class Functions():
	"""
	Built-in functions
	"""

	def __init__(self):
		self._repository = repository.Repository()

	def sub_func(self, mo):
		sorig = mo.string[mo.start():mo.end()]
		if mo.lastindex != 1:
			return sorig
		s = mo.string[mo.start(1):mo.end(1)]
		if len(s) == 0:
			return sorig
		sl = re.split(r'(?<!\\):', s)
		sl = map(lambda v: str(v).replace("\:", ":"), sl)
		if not re.match(r'\w+$', sl[0]):
			log.error("invalid function name '%s'" % sl[0])
			return sorig
		try:
			f = self._repository.load_func(sl[0])
		except ImportError:
			log.error("function '%s' not implemented" % sl[0])
			return sorig
		s = f.execute(sl[1:])
		if s is None:
			return sorig
		return s

	def expand(self, s):
		if s is None:
			return s
		r = re.compile(r'(?<!\\)\${f:([^}]+)}')
		# expand functions and convert all \${f:*} to ${f:*} (unescape)
		return re.sub(r'\\(\${f:[^}]+})', r'\1', r.sub(self.sub_func, s))
