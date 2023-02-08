import os
import re
import tuned.logs
from .functions import functions as functions
import tuned.consts as consts
from tuned.utils.commands import commands
from tuned.utils.config_parser import ConfigParser, Error

log = tuned.logs.get()

class Variables():
	"""
	Storage and processing of variables used in profiles
	"""

	def __init__(self):
		self._cmd = commands()
		self._lookup_re = {}
		self._lookup_env = {}
		self._functions = functions.Functions()

	def _add_env_prefix(self, s, prefix):
		if s.find(prefix) == 0:
			return s
		return prefix + s

	def _check_var(self, variable):
		return re.match(r'\w+$',variable)

	def add_variable(self, variable, value):
		if value is None:
			return
		s = str(variable)
		if not self._check_var(variable):
			log.error("variable definition '%s' contains unallowed characters" % variable)
			return
		v = self.expand(value)
		# variables referenced by ${VAR}, $ can be escaped by two $,
		# i.e. the following will not expand: $${VAR}
		self._lookup_re[r'(?<!\\)\${' + re.escape(s) + r'}'] = v
		self._lookup_env[self._add_env_prefix(s, consts.ENV_PREFIX)] = v

	def add_from_file(self, filename):
		if not os.path.exists(filename):
			log.error("unable to find variables_file: '%s'" % filename)
			return
		try:
			config = ConfigParser(delimiters=('='), inline_comment_prefixes=('#'), allow_no_value=True, strict=False)
			config.optionxform = str
			with open(filename) as f:
				config.read_string("[" + consts.MAGIC_HEADER_NAME + "]\n" + f.read(), filename)
		except Error:
			log.error("error parsing variables_file: '%s'" % filename)
			return
		for s in config.sections():
			for o in config.options(s):
				self.add_variable(o, config.get(s, o, raw=True))

	def add_from_cfg(self, cfg):
		for item in cfg:
			if str(item) == "include":
				self.add_from_file(os.path.normpath(cfg[item]))
			else:
				self.add_variable(item, cfg[item])

	# expand static variables (no functions)
	def expand_static(self, value):
		return re.sub(r'\\(\${\w+})', r'\1', self._cmd.multiple_re_replace(self._lookup_re, value))

	def expand(self, value):
		if value is None:
			return None
		# expand variables and convert all \${VAR} to ${VAR} (unescape)
		s = self.expand_static(str(value))
		# expand built-in functions
		return self._functions.expand(s)

	def get_env(self):
		return self._lookup_env
