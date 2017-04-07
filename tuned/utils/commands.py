import errno
import tuned.logs
import copy
import os
import shutil
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

	# escape escape character (by default '\')
	def escape(self, s, what_escape = "\\", escape_by = "\\"):
		return s.replace(what_escape, "%s%s" % (escape_by, what_escape))

	# clear escape characters (by default '\')
	def unescape(self, s, escape_char = "\\"):
		return s.replace(escape_char, "")

	# add spaces to align s2 to pos, returns resulting string: s1 + spaces + s2
	def align_str(self, s1, pos, s2):
		return s1 + " " * (pos - len(s1)) + s2

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
	def multiple_re_replace(self, d, s, r = None, flags = 0):
		if d is None:
			if r is None:
				return s
		else:
			if len(d) == 0 or s is None:
				return s
		if r is None:
			r = self.re_lookup_compile(d)
		return r.sub(lambda mo: d.values()[mo.lastindex - 1], s, flags)

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

	def write_to_file(self, f, data, makedir = False, no_error = False):
		self._debug("Writing to file: '%s' < '%s'" % (f, data))
		if makedir:
			d = os.path.dirname(f)
			if os.path.isdir(d):
				makedir = False
		try:
			if makedir:
				os.makedirs(d)
			fd = open(f, "w")
			fd.write(str(data))
			fd.close()
			rc = True
		except (OSError,IOError) as e:
			rc = False
			if not no_error:
				self._error("Writing to file '%s' error: '%s'" % (f, e))
		return rc

	def read_file(self, f, err_ret = "", no_error = False):
		old_value = err_ret
		try:
			f = open(f, "r")
			old_value = f.read()
			f.close()
		except (OSError,IOError) as e:
			if not no_error:
				self._error("Error when reading file '%s': '%s'" % (f, e))
		self._debug("Read data from file: '%s' > '%s'" % (f, old_value))
		return old_value

	def rmtree(self, f, no_error = False):
		self._debug("Removing tree: '%s'" % f)
		if os.path.exists(f):
			try:
				shutil.rmtree(f, no_error)
			except OSError as error:
				if not no_error:
					log.error("cannot remove tree '%s': '%s'" % (f, str(error)))
				return False
		return True

	def unlink(self, f, no_error = False):
		self._debug("Removing file: '%s'" % f)
		if os.path.exists(f):
			try:
				os.unlink(f)
			except OSError as error:
				if not no_error:
					log.error("cannot remove file '%s': '%s'" % (f, str(error)))
				return False
		return True

	def rename(self, src, dst, no_error = False):
		self._debug("Renaming file '%s' to '%s'" % (src, dst))
		try:
			os.rename(src, dst)
		except OSError as error:
			if not no_error:
				log.error("cannot rename file '%s' to '%s': '%s'" % (src, dst, str(error)))
			return False
		return True

	def copy(self, src, dst, no_error = False):
		try:
			log.debug("copying file '%s' to '%s'" % (src, dst))
			shutil.copy(src, dst)
		except IOError as e:
			if not no_error:
				log.error("cannot copy file '%s' to '%s': %s" % (src, dst, e))

	def replace_in_file(self, f, pattern, repl):
		data = self.read_file(f)
		if len(data) <= 0:
			return False;
		return self.write_to_file(f, re.sub(pattern, repl, data, flags = re.MULTILINE))

	# do multiple replaces in file 'f' by using dictionary 'd',
	# e.g.: d = {"re1": val1, "re2": val2, ...}
	def multiple_replace_in_file(self, f, d):
		data = self.read_file(f)
		if len(data) <= 0:
			return False;
		return self.write_to_file(f, self.multiple_re_replace(d, data, flags = re.MULTILINE))

	# makes sure that options from 'd' are set to values from 'd' in file 'f',
	# when needed it edits options or add new options if they don't
	# exist and 'add' is set to True, 'd' has the following form:
	# d = {"option_1": value_1, "option_2": value_2, ...}
	def add_modify_option_in_file(self, f, d, add = True):
		data = self.read_file(f)
		for opt in d:
			o = str(opt)
			v = str(d[opt])
			if re.search(r"\b" + o + r"\s*=.*$", data, flags = re.MULTILINE) is None:
				if add:
					if len(data) > 0 and data[-1] != "\n":
						data += "\n"
					data += "%s=\"%s\"\n" % (o, v)
			else:
				data = re.sub(r"\b(" + o + r"\s*=).*$", r"\1" + "\"" + v + "\"", data, flags = re.MULTILINE)

		return self.write_to_file(f, data)

	# "no_errors" can be list of return codes not treated as errors, if 0 is in no_errors, it means any error
	# returns (retcode, out), where retcode is exit code of the executed process or -errno if
	# OSError or IOError exception happened
	def execute(self, args, shell = False, cwd = None, no_errors = []):
		retcode = 0
		if self._environment is None:
			self._environment = os.environ.copy()
			self._environment["LC_ALL"] = "C"

		self._debug("Executing %s." % str(args))
		out = ""
		try:
			proc = Popen(args, stdout = PIPE, stderr = PIPE, env = self._environment, shell = shell, cwd = cwd, close_fds = True)
			out, err = proc.communicate()

			retcode = proc.returncode
			if retcode and not retcode in no_errors and not 0 in no_errors:
				err_out = err[:-1]
				if len(err_out) == 0:
					err_out = out[:-1]
				self._error("Executing %s error: %s" % (args[0], err_out))
		except (OSError, IOError) as e:
			retcode = -e.errno if e.errno is not None else -1
			if not abs(retcode) in no_errors and not 0 in no_errors:
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
		if type(l) is list:
			ll = l
		else:
			ll = str(l).split(",")
		ll2 = []
		hexmask = False
		hv = ""
		# Remove commas from hexmasks
		for v in ll:
			sv = str(v)
			if hexmask:
				if len(sv) == 0:
					hexmask = False
					ll2.append(hv)
					hv = ""
				else:
					hv += sv
			else:
				if sv[0:2].lower() == "0x":
					hexmask = True
					hv = sv
				else:
					if len(sv) > 0:
						ll2.append(sv)
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

	# Packs CPU list, i.e. 1, 2, 3  will be converted to 1-3. It unpacks the
	# CPU list through cpulist_unpack first, so see its description about the
	# details of the input syntax
	def cpulist_pack(self, l):
		l = self.cpulist_unpack(l)
		if l is None or len(l) == 0:
			return l
		i = 0
		j = i
		rl = []
		while i + 1 < len(l):
			if l[i + 1] - l[i] != 1:
				if j != i:
					rl.append(str(l[j]) + "-" + str(l[i]))
				else:
					rl.append(str(l[i]))
				j = i + 1
			i += 1
		if j + 1 < len(l):
			rl.append(str(l[j]) + "-" + str(l[-1]))
		else:
			rl.append(str(l[-1]))
		return rl

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
