import os
import re
import tuned.logs
import tuned.consts as consts
from tuned.utils.commands import commands
from configobj import ConfigObj

log = tuned.logs.get()

class Variables():
	"""
	Storage and processing of variables used in profiles
	"""

	def __init__(self):
		self._cmd = commands()
		self._lookup_re = {}
		self._lookup_env = {}

	def _add_env_prefix(self, s, prefix):
		if s.find(prefix) == 0:
			return s
		return prefix + s

	def add_variable(self, variable, value):
		if value is None:
			return
		s = str(variable)
		v = self.expand(value)
		self._lookup_re[r'\$' + re.escape(s) + r'\b'] = v
		self._lookup_env[self._add_env_prefix(s, consts.ENV_PREFIX)] = v

	def add_dict(self, d):
		for item in d:
			self.add_variable(item, d[item])

	def add_from_file(self, filename):
		if not os.path.exists(filename):
			log.error("unable to find variables_file: '%s'" % filename)
			return
		try:
			config = ConfigObj(filename, raise_errors = True)
		except ConfigObjError:
			log.error("error parsing variables_file: '%s'" % filename)
			return
		for item in config:
			if isinstance(config[item], dict):
				self.add_dict(config[item])
			else:
				self.add_variable(item, config[item])

	def add_from_cfg(self, cfg, dir_name):
		for item in cfg:
			if str(item) == "include":
				self.add_from_file(os.path.normpath(os.path.join(dir_name, cfg[item])))
			else:
				self.add_variable(item, cfg[item])

	def expand(self, value):
		if value is None:
			return None
		return self._cmd.multiple_re_replace(self._lookup_re, str(value))

	def get_env(self):
		return self._lookup_env
