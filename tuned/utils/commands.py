import errno
import hashlib
import tuned.logs
import copy
import os
import shutil
import tuned.consts as consts
import re
from subprocess import *
from tuned.exceptions import TunedException

log = tuned.logs.get()

class commands:

	def __init__(self, logging = True):
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
		return re.sub(r'\s+', ' ', str(s)).strip()

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
		return re.compile("(%s)" % ")|(".join(list(d.keys())))

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
		return r.sub(lambda mo: list(d.values())[mo.lastindex - 1], s, flags)

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
			return list(d.values())[mo.lastindex - 1]
		return None

	def write_to_file(self, f, data, makedir = False, no_error = False, ignore_same = False):
		"""Write data to a file.

		Parameters:
		f -- filename where to write
		data -- data to write
		makedir -- if True and the path doesn't exist, it will be created
		no_error -- if True errors are silenced, it can be also list of ignored errnos
		ignore_same -- if True and the write would not change the file, it is skipped

		Return:
		bool -- True on success
		"""
		self._debug("Writing to file: '%s' < '%s'" % (f, data))
		if makedir:
			d = os.path.dirname(f)
			if os.path.isdir(d):
				makedir = False
		try:
			if makedir:
				os.makedirs(d)
			if ignore_same and self.read_file(f, no_error=True).strip() == str(data):
				self._debug("Skipping the write to file '%s', the content would not change" % f)
				return True
			fd = open(f, "w")
			fd.write(str(data))
			fd.close()
			rc = True
		except (OSError, IOError) as e:
			rc = False
			if isinstance(no_error, bool) and not no_error or \
				isinstance(no_error, list) and e.errno not in no_error:
					self._error("Writing to file '%s' error: '%s'" % (f, e))
		return rc

	def read_file(self, f, err_ret = "", no_error = False):
		old_value = err_ret
		try:
			fd = open(f, "r")
			old_value = fd.read()
			fd.close()
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
			return True
		except IOError as e:
			if not no_error:
				log.error("cannot copy file '%s' to '%s': %s" % (src, dst, e))
			return False

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
				data = re.sub(r"\b(" + o + r"\s*=).*$", r"\1" + "\"" + self.escape(v) + "\"", data, flags = re.MULTILINE)

		return self.write_to_file(f, data)

	# calcualates md5sum of file 'f'
	def md5sum(self, f):
		data = self.read_file(f)
		return hashlib.md5(str(data).encode("utf-8")).hexdigest()

	# calcualates sha256sum of file 'f'
	def sha256sum(self, f):
		data = self.read_file(f)
		return hashlib.sha256(str(data).encode("utf-8")).hexdigest()

	# returns machine ID or empty string "" in case of error
	def get_machine_id(self, no_error = True):
		return self.read_file(consts.MACHINE_ID_FILE, no_error).strip()

	# "no_errors" can be list of return codes not treated as errors, if 0 is in no_errors, it means any error
	# returns (retcode, out), where retcode is exit code of the executed process or -errno if
	# OSError or IOError exception happened
	def execute(self, args, shell = False, cwd = None, env = {}, no_errors = [], return_err = False):
		retcode = 0
		_environment = os.environ.copy()
		_environment["LC_ALL"] = "C"
		_environment.update(env)

		self._debug("Executing %s." % str(args))
		out = ""
		err_msg = None
		try:
			proc = Popen(args, stdout = PIPE, stderr = PIPE, \
					env = _environment, \
					shell = shell, cwd = cwd, \
					close_fds = True, \
					universal_newlines = True)
			out, err = proc.communicate()

			retcode = proc.returncode
			if retcode and not retcode in no_errors and not 0 in no_errors:
				err_out = err[:-1]
				if len(err_out) == 0:
					err_out = out[:-1]
				err_msg = "Executing '%s' error: %s" % (' '.join(args), err_out)
				if not return_err:
					self._error(err_msg)
		except (OSError, IOError) as e:
			retcode = -e.errno if e.errno is not None else -1
			if not abs(retcode) in no_errors and not 0 in no_errors:
				err_msg = "Executing '%s' error: %s" % (' '.join(args), e)
				if not return_err:
					self._error(err_msg)
		if return_err:
			return retcode, out, err_msg
		else:
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
		return cpu == "0" or self.read_file("/sys/devices/system/cpu/cpu%s/online" % scpu, err_ret = "1", no_error = True).strip() == "1"

	# Converts hexadecimal CPU mask to CPU list
	def hex2cpulist(self, mask):
		if mask is None:
			return None
		mask = str(mask).replace(",", "")
		try:
			m = int(mask, 16)
		except ValueError:
			log.error("invalid hexadecimal mask '%s'" % str(mask))
			return []
		return self.bitmask2cpulist(m)

	# Converts an integer bitmask to a list of cpus (e.g. [0,3,4])
	def bitmask2cpulist(self, mask):
		cpu = 0
		cpus = []
		while mask > 0:
			if mask & 1:
				cpus.append(cpu)
			mask >>= 1
			cpu += 1
		return cpus

	# Unpacks CPU list, i.e. 1-3 will be converted to 1, 2, 3, supports
	# hexmasks that needs to be prefixed by "0x". Hexmasks can have commas,
	# which will be removed. If combining hexmasks with CPU list they need
	# to be separated by ",,", e.g.: 0-3, 0xf,, 6. It also supports negation
	# cpus by specifying "^" or "!", e.g.: 0-5, ^3, will output the list as
	# "0,1,2,4,5" (excluding 3). Note: negation supports only cpu numbers.
	# If "strip_chars" is not None and l is not list, we try strip characters.
	# It should be string with list of chars that is send to string.strip method
	# Default is english single and double quotes ("') rhbz#1891036
	def cpulist_unpack(self, l, strip_chars='\'"'):
		rl = []
		if l is None:
			return l
		ll = l
		if type(ll) is not list:
			if strip_chars is not None:
				ll = str(ll).strip(strip_chars)
			ll = str(ll).split(",")
		ll2 = []
		negation_list = []
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
				elif sv and (sv[0] == "^" or sv[0] == "!"):
					nl = sv[1:].split("-")
					try:
						if (len(nl) > 1):
							negation_list += list(range(
								int(nl[0]),
								int(nl[1]) + 1
								)
							)
						else:
							negation_list.append(int(sv[1:]))
					except ValueError:
						return []
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
						rl += list(range(int(vl[0]), int(vl[1]) + 1))
					else:
						rl.append(int(vl[0]))
				except ValueError:
					return []
		cpu_list = sorted(list(set(rl)))

		# Remove negated cpus after expanding
		for cpu in negation_list:
			if cpu in cpu_list:
				cpu_list.remove(cpu)
		return cpu_list

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
		online = self.cpulist_unpack(self.read_file("/sys/devices/system/cpu/online"))
		return list(set(online) - set(cpus))

	# Converts CPU list to hexadecimal CPU mask
	def cpulist2hex(self, l):
		if l is None:
			return None
		ul = self.cpulist_unpack(l)
		if ul is None:
			return None
		m = self.cpulist2bitmask(ul)
		s = "%x" % m
		ls = len(s)
		if ls % 8 != 0:
			ls += 8 - ls % 8
		s = s.zfill(ls)
		return ",".join(s[i:i + 8] for i in range(0, len(s), 8))

	def cpulist2bitmask(self, l):
		m = 0
		for v in l:
			m |= pow(2, v)
		return m

	def cpulist2string(self, l, prefix = ""):
		return ",".join((prefix + str(v)) for v in l)

	# Converts string s consisting of "dev1,dev2,dev3,..." to list ["dev1", "dev2, "dev3", ...],
	# whitespaces are ignored, cpu lists are supported with the prefix "cpulist:", e.g.
	# "cpulist:0-2,4" is converted to ["cpu0", "cpu1", "cpu2", "cpu4"]. If device name starts
	# with "cpulist:" write it as "cpulist:cpulist:". Escape commas in name with the "\,".
	def devstr2devs(self, s):
		if s[0:8].lower() == "cpulist:":
			s = s[8:]
			if s[0:8].lower() != "cpulist:":
				return [("cpu" + str(v)) for v in self.cpulist_unpack(s)]
		l = re.split(r"\s*(?<!\\),\s*", s)
		return [str(v).replace(r"\,", ",") for v in l]

	# Do not make balancing on patched Python 2 interpreter (rhbz#1028122).
	# It means less CPU usage on patched interpreter. On non-patched interpreter
	# it is not allowed to sleep longer than 50 ms.
	def wait(self, terminate, time):
		try:
			return terminate.wait(time, False)
		except TypeError as e:
			return terminate.wait(time)

	def get_size(self, s):
		s = str(s).strip().upper()
		for unit in ["KB", "MB", "GB", ""]:
			unit_ix = s.rfind(unit)
			if unit_ix == -1:
				continue
			try:
				val = int(s[:unit_ix])
				u = s[unit_ix:]
				if u == "KB":
					val *= 1024
				elif u == "MB":
					val *= 1024 * 1024
				elif u == "GB":
					val *= 1024 * 1024 * 1024
				elif u != "":
					val = None
				return val
			except ValueError:
				return None

	def get_active_profile(self):
		profile_name = ""
		mode = ""
		try:
			with open(consts.ACTIVE_PROFILE_FILE, "r") as f:
				profile_name = f.read().strip()
		except IOError as e:
			if e.errno != errno.ENOENT:
				raise TunedException("Failed to read active profile: %s" % e)
		except (OSError, EOFError) as e:
			raise TunedException("Failed to read active profile: %s" % e)
		try:
			with open(consts.PROFILE_MODE_FILE, "r") as f:
				mode = f.read().strip()
				if mode not in ["", consts.ACTIVE_PROFILE_AUTO, consts.ACTIVE_PROFILE_MANUAL]:
					raise TunedException("Invalid value in file %s." % consts.PROFILE_MODE_FILE)
		except IOError as e:
			if e.errno != errno.ENOENT:
				raise TunedException("Failed to read profile mode: %s" % e)
		except (OSError, EOFError) as e:
			raise TunedException("Failed to read profile mode: %s" % e)
		if mode == "":
			manual = None
		else:
			manual = mode == consts.ACTIVE_PROFILE_MANUAL
		if profile_name == "":
			profile_name = None
		return (profile_name, manual)

	def save_active_profile(self, profile_name, manual):
		try:
			with open(consts.ACTIVE_PROFILE_FILE, "w") as f:
				if profile_name is not None:
					f.write(profile_name + "\n")
		except (OSError,IOError) as e:
			raise TunedException("Failed to save active profile: %s" % e.strerror)
		try:
			with open(consts.PROFILE_MODE_FILE, "w") as f:
				mode = consts.ACTIVE_PROFILE_MANUAL if manual else consts.ACTIVE_PROFILE_AUTO
				f.write(mode + "\n")
		except (OSError,IOError) as e:
			raise TunedException("Failed to save profile mode: %s" % e.strerror)

	def get_post_loaded_profile(self):
		profile_name = ""
		try:
			with open(consts.POST_LOADED_PROFILE_FILE, "r") as f:
				profile_name = f.read().strip()
		except IOError as e:
			if e.errno != errno.ENOENT:
				raise TunedException("Failed to read the active post-loaded profile: %s" % e)
		except (OSError, EOFError) as e:
			raise TunedException("Failed to read the active post-loaded profile: %s" % e)
		if profile_name == "":
			profile_name = None
		return profile_name

	def save_post_loaded_profile(self, profile_name):
		try:
			with open(consts.POST_LOADED_PROFILE_FILE, "w") as f:
				if profile_name is not None:
					f.write(profile_name + "\n")
		except (OSError,IOError) as e:
			raise TunedException("Failed to save the active post-loaded profile: %s" % e.strerror)

	# Translates characters in 'text' from 'source_chars' to 'dest_chars'
	def tr(self, text, source_chars, dest_chars):
		try:
			trans = str.maketrans(source_chars, dest_chars)
		except AttributeError:
			import string
			trans = string.maketrans(source_chars, dest_chars)
		return text.translate(trans)

	# Checks if name contains only valid characters and has valid length or is empty string or None
	def is_valid_name(self, name):
		return not name or (all(c in consts.NAMES_ALLOWED_CHARS for c in name) and len(name) <= consts.NAMES_MAX_LENGTH)

	def getconf(self, variable):
		return check_output(["getconf", variable]).decode().strip()

	# Gets list of available CPUs
	def get_cpus(self):
		cpus = self.read_file(consts.SYSFS_CPUS_PRESENT_PATH)
		# fallback to single core CPU if sysfs is unavailable
		return self.cpulist_unpack(cpus) if cpus else [ 0 ]
