import tuned.logs
import copy
import os
import tuned.consts as consts
from configobj import ConfigObj
import re
from subprocess import *

log = tuned.logs.get()

class commands:

	def __init__(self, logging = True):
		self._environment = None
		self._logging = logging

	def _error(self, msg):
		if self._logging:
			log.error(msg)

	def _debug(self, msg):
		if self._logging:
			log.debug(msg)

	def get_bool(self, value):
		v = str(value).upper().strip()
		return {"Y":"1", "YES":"1", "T":"1", "TRUE":"1", "N":"0", "NO":"0", "F":"0", "FALSE":"0"}.get(v, value)

	def write_to_file(self, f, data):
		self._debug("Writing to file: %s < %s" % (f, data))
		try:
			fd = open(f, "w")
			fd.write(str(data))
			fd.close()
			rc = True
		except (OSError,IOError) as e:
			rc = False
			self._error("Writing to file %s error: %s" % (f, e))
		return rc

	def read_file(self, f, err_ret = ""):
		old_value = err_ret
		try:
			f = open(f, "r")
			old_value = f.read()
			f.close()
		except (OSError,IOError) as e:
			self._error("Reading %s error: %s" % (f, e))
		return old_value

	def replace_in_file(self, f, pattern, repl):
		data = self.read_file(f)
		if len(data) <= 0:
			return False;
		return self.write_to_file(f, re.sub(pattern, repl, data, flags = re.MULTILINE))

	def execute(self, args):
		retcode = None
		if self._environment is None:
			self._environment = os.environ.copy()
			self._environment["LC_ALL"] = "C"

		self._debug("Executing %s." % str(args))
		out = ""
		try:
			proc = Popen(args, stdout=PIPE, stderr=PIPE, env=self._environment, close_fds=True)
			out, err = proc.communicate()

			retcode = proc.returncode
			if retcode:
				err_out = err[:-1]
				if len(err_out) == 0:
					err_out = out[:-1]
				self._error("Executing %s error: %s" % (args[0], err_out))
		except (OSError,IOError) as e:
			retcode = -1
			self._error("Executing %s error: %s" % (args[0], e))
		return retcode, out

	# Helper for parsing kernel options like:
	# [always] never
	# It will return 'always'
	def get_active_option(self, options, dosplit = True):
		m = re.match(r'.*\[([^\]]+)\].*', options)
		if m:
			return m.group(1)
		if dosplit:
			return options.split()[0]
		return options

	def recommend_profile(self):
		profile = consts.DEFAULT_PROFILE
		for f in consts.LOAD_DIRECTORIES:
			config = ConfigObj(os.path.join(f, consts.AUTODETECT_FILE))
			for section in reversed(config.keys()):
				match1 = match2 = True
				for option in config[section].keys():
					value = config[section][option]
					if value == "":
						value = r"^$"
					if option == "virt":
						if not re.match(value, self.execute("virt-what")[1], re.S):
							match1 = False
					elif option == "system":
						if not re.match(value, self.read_file(consts.SYSTEM_RELEASE_FILE), re.S):
							match2 = False
				if match1 and match2:
					profile = section
		return profile

	# Do not make balancing on patched Python 2 interpreter (rhbz#1028122).
	# It means less CPU usage on patchet interpreter. On non-patched interpreter
	# it is not allowed to sleep longer than 50 ms.
	def wait(self, terminate, time):
		try:
			return terminate.wait(time, False)
		except:
			return terminate.wait(time)
