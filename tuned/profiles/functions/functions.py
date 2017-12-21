import os
import re
import glob
from . import repository
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
		self._parse_init()

	def _parse_init(self, s = ""):
		self._cnt = 0
		self._str = s
		self._len = len(s)
		self._stack = []
		self._esc = False

	def _curr_char(self):
		return self._str[self._cnt] if self._cnt < self._len else ""

	def _curr_substr(self, _len):
		return self._str[self._cnt:self._cnt + _len]

	def _push_pos(self, esc):
		self._stack.append((esc, self._cnt))

	def _sub(self, a, b, s):
		self._str = self._str[:a] + s + self._str[b + 1:]
		self._len = len(self._str)
		self._cnt += len(s) - (b - a + 1)
		if self._cnt < 0:
			self._cnt = 0

	def _process_func(self, _from):
		sl = re.split(r'(?<!\\):', self._str[_from:self._cnt])
		if sl[0] != "${f":
			return
		sl = [str(v).replace("\:", ":") for v in sl]
		if not re.match(r'\w+$', sl[1]):
			log.error("invalid function name '%s'" % sl[1])
			return
		try:
			f = self._repository.load_func(sl[1])
		except ImportError:
			log.error("function '%s' not implemented" % sl[1])
			return
		s = f.execute(sl[2:])
		if s is None:
			return
		self._sub(_from, self._cnt, s)

	def _process(self, s):
		self._parse_init(s)
		while self._cnt < self._len:
			if self._curr_char() == "}":
				try:
					si = self._stack.pop()
				except IndexError:
					log.error("invalid variable syntax, non pair '}' in: '%s'" % s)
					return self._str
				# if not escaped
				if not si[0]:
					self._process_func(si[1])
			elif self._curr_substr(2) == "${":
				self._push_pos(self._esc)
			if self._curr_char() == "\\":
				self._esc = True
			else:
				self._esc = False
			self._cnt += 1
		if len(self._stack):
			log.error("invalid varialbe syntax, non pair '{' in: '%s'" % s)
		return self._str

	def expand(self, s):
		if s is None or s == "":
			return s
		# expand functions and convert all \${f:*} to ${f:*} (unescape)
		return re.sub(r'\\(\${f:.*})', r'\1', self._process(s))
