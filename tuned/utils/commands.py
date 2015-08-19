import errno
import tuned.logs
import copy
import os
import tuned.consts as consts
from configobj import ConfigObj, ConfigObjError
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

	def unquote(self, v):
		return re.sub("^\"(.*)\"$", r"\1", v)

	# convert dictionary 'd' to flat list and return it
	# it uses sort on the dictionary items to return consistent results
	# for directories with different inserte/delete history
	def dict2list(self, d):
		l = []
		if d is not None:
			for i in sorted(d.items()):
				l += list(i)
		return l

	# Compile regex to speedup multiple_re_replace or re_lookup
	def re_lookup_compile(self, d):
		if d is None:
			return None
		return re.compile("(%s)" % ")|(".join(d.keys()))

	# Do multiple regex replaces in 's' according to lookup table described by
	# dictionary 'd', e.g.: d = {"re1": "replace1", "re2": "replace2", ...}
	# r can be regex precompiled by re_lookup_compile for speedup
	def multiple_re_replace(self, d, s, r = None):
		if len(d) == 0 or s is None:
			return s
		if r is None:
			r = self.re_lookup_compile(d)
		return r.sub(lambda mo: d.values()[mo.lastindex - 1], s)

	# Do regex lookup on 's' according to lookup table described by
	# dictionary 'd' and return corresponding value from the dictionary,
	# e.g.: d = {"re1": val1, "re2": val2, ...}
	# r can be regex precompiled by re_lookup_compile for speedup
	def re_lookup(self, d, s, r = None):
		if len(d) == 0 or s is None:
			return None
		if r is None:
			r = self.re_lookup_compile(d)
		mo = r.search(s)
		if mo:
			return d.values()[mo.lastindex - 1]
		return None

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
		retcode = 0
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
		except (OSError, IOError) as e:
			retcode = e.errno if e.errno is not None else -1
			if not retcode in no_errors:
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
		mask = str(mask).replace(",", "")
		cpu = 0
		cpus = []
		try:
			m = int(mask, 16)
		except ValueError:
			log.error("invalid hexadecimal mask '%s'" % str(mask))
			return []
		while m > 0:
			if m & 1:
				cpus.append(cpu)
			m >>= 1
			cpu += 1
		return cpus

	# Unpacks CPU list, i.e. 1-3 will be converted to 1, 2, 3, supports
	# hexmasks that needs to be prefixed by "0x". Hexmasks can have commas,
	# which will be removed. If combining hexmasks with CPU list they need
	# to be separated by ",,", e.g.: 0-3, 0xf,, 6
	def cpulist_unpack(self, l):
		rl = []
		if l is None:
			return l
		ll = str(l).split(",")
		ll2 = []
		hexmask = False
		hv = ""
		# Remove commas from hexmasks
		for v in ll:
			if hexmask:
				if len(v) == 0:
					hexmask = False
					ll2.append(hv)
					hv = ""
				else:
					hv += v
			else:
				if v[0:2].lower() == "0x":
					hexmask = True
					hv = v
				else:
					if len(v) > 0:
						ll2.append(v)
		if len(hv) > 0:
			ll2.append(hv)
		for v in ll2:
			vl = v.split("-")
			if v[0:2].lower() == "0x":
				rl += self.hex2cpulist(v)
			else:
				try:
					if len(vl) > 1:
						rl += range(int(vl[0]), int(vl[1]) + 1)
					else:
						rl.append(int(vl[0]))
				except ValueError:
					return []
		return sorted(list(set(rl)))

	# Inverts CPU list (i.e. makes its complement)
	def cpulist_invert(self, l):
		cpus = self.cpulist_unpack(l)
		present = self.cpulist_unpack(self.read_file("/sys/devices/system/cpu/present"))
		return list(set(present) - set(cpus))

	# Converts CPU list to hexadecimal CPU mask
	def cpulist2hex(self, l):
		if l is None:
			return None
		m = 0
		ul = self.cpulist_unpack(l)
		if ul is None:
			return None
		for v in ul:
			m |= pow(2, v)
		s = "%x" % m
		ls = len(s)
		if ls % 8 != 0:
			ls += 8 - ls % 8
		s = s.zfill(ls)
		return ",".join(s[i:i + 8] for i in range(0, len(s), 8))

	def recommend_profile(self, hardcoded = False):
		profile = consts.DEFAULT_PROFILE
		if hardcoded:
			return profile
		r = re.compile(r",[^,]*$")
		for f in consts.LOAD_DIRECTORIES:
			try:
				fname = os.path.join(f, consts.AUTODETECT_FILE)
				config = ConfigObj(fname, list_values = False, interpolation = False)
				for section in reversed(config.keys()):
					match = True
					for option in config[section].keys():
						value = config[section][option]
						if value == "":
							value = r"^$"
						if option == "virt":
							if not re.match(value, self.execute("virt-what")[1], re.S):
								match = False
						elif option == "system":
							if not re.match(value, self.read_file(consts.SYSTEM_RELEASE_FILE), re.S):
								match = False
						elif option[0] == "/":
							if not os.path.exists(option) or not re.match(value, self.read_file(option), re.S):
								match = False
					if match:
						# remove the ",.*" suffix
						profile = r.sub("", section)
			except (IOError, OSError, ConfigObjError) as e:
				log.error("error parsing '%s', %s" % (fname, e))
		return profile

	# Do not make balancing on patched Python 2 interpreter (rhbz#1028122).
	# It means less CPU usage on patchet interpreter. On non-patched interpreter
	# it is not allowed to sleep longer than 50 ms.
	def wait(self, terminate, time):
		try:
			return terminate.wait(time, False)
		except:
			return terminate.wait(time)
