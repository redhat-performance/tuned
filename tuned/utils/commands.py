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

	def remove_ws(self, s):
		return re.sub('\s+', ' ', s).strip()

	# convert dictionary 'd' to flat list and return it
	# it uses sort on the dictionary items to return consistent results
	# for directories with different inserte/delete history
	def dict2list(self, d):
		l = []
		if d is not None:
			for i in sorted(d.items()):
				l += list(i)
		return l

	# Do multiple regex replaces in 's' according to lookup table described by
	# dictionary 'd', e.g.: d = {"re1": "replace1", "re2": "replace2"}
	def multiple_re_replace(self, d, s):
		if len(d) == 0 or s is None:
			return s
		r = re.compile("(%s)" % ")|(".join(d.keys()))
		return r.sub(lambda mo: d.values()[mo.lastindex - 1], s)

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

	def read_file(self, f, err_ret = "", no_error = False):
		old_value = err_ret
		try:
			f = open(f, "r")
			old_value = f.read()
			f.close()
		except (OSError,IOError) as e:
			if not no_error:
				self._error("Reading %s error: %s" % (f, e))
		return old_value

	def replace_in_file(self, f, pattern, repl):
		data = self.read_file(f)
		if len(data) <= 0:
			return False;
		return self.write_to_file(f, re.sub(pattern, repl, data, flags = re.MULTILINE))

	# "no_errors" can be list of return codes not treated as errors
	def execute(self, args, no_errors = []):
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
			if retcode and not retcode in no_errors:
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

	# Checks whether CPU is online
	def is_cpu_online(self, cpu):
		scpu = str(cpu)
		# CPU0 is always online
		return cpu == "0" or self.read_file("/sys/devices/system/cpu/cpu%s/online" % scpu, no_error = True).strip() == "1"

	# Converts hexadecimal CPU mask to CPU list
	def hex2cpulist(self, mask):
		if mask is None:
			return None
		cpu = 0
		cpus = []
		try:
			m = int(mask, 16)
		except ValueError:
			log.error("invalid hexadecimal mask '%s'" % str(mask))
			return []
		while m > 0:
			if m & 1:
				cpus.append(str(cpu))
			m >>= 1
			cpu += 1
		return cpus

	# Unpacks CPU list, i.e. 1-3 will be converted to 1, 2, 3
	def unpack_cpulist(self, l):
		rl = []
		if l is None:
			return l
		ll = str(l).split(",")
		for v in ll:
			vl = v.split("-")
			try:
				if len(vl) > 1:
					rl += range(int(vl[0]), int(vl[1]) + 1)
				else:
					rl.append(int(vl[0]))
			except ValueError:
				return None
		return sorted(list(set(rl)))

	# Converts CPU list to hexadecimal CPU mask
	def cpulist2hex(self, l):
		if l is None:
			return None
		m = 0
		ul = self.unpack_cpulist(l)
		if ul is None:
			return None
		for v in self.unpack_cpulist(l):
			m |= pow(2, v)
		return "0x%08x" % m

	def recommend_profile(self):
		profile = consts.DEFAULT_PROFILE
		for f in consts.LOAD_DIRECTORIES:
			config = ConfigObj(os.path.join(f, consts.AUTODETECT_FILE), list_values = False, interpolation = False)
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
