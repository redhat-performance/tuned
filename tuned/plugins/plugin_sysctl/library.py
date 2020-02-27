import errno
import os

DEPRECATED_SYSCTL_OPTIONS = [ "base_reachable_time", "retrans_time" ]
SYSCTL_CONFIG_DIRS = [ "/run/sysctl.d", "/etc/sysctl.d" ]

class SysctlLib(object):
	def __init__(self, file_handler, listdir, logger):
		self._file_handler = file_handler
		self._listdir = listdir
		self._log = logger

	def apply_system_sysctl(self):
		files = {}
		for d in SYSCTL_CONFIG_DIRS:
			try:
				flist = self._listdir(d)
			except OSError:
				continue
			for fname in flist:
				if not fname.endswith(".conf"):
					continue
				if fname not in files:
					files[fname] = d

		for fname in sorted(files.keys()):
			d = files[fname]
			path = "%s/%s" % (d, fname)
			self._apply_sysctl_config_file(path)
		self._apply_sysctl_config_file("/etc/sysctl.conf")

	def _apply_sysctl_config_file(self, path):
		self._log.debug("Applying sysctl settings from file %s" % path)
		try:
			content = self._file_handler.read(path)
			lines = content.split("\n")
			for lineno, line in enumerate(lines, 1):
				self._apply_sysctl_config_line(path, lineno, line)
			self._log.debug("Finished applying sysctl settings from file %s"
					% path)
		except (OSError, IOError) as e:
			if e.errno != errno.ENOENT:
				self._log.error("Error reading sysctl settings from file %s: %s"
						% (path, str(e)))

	def _apply_sysctl_config_line(self, path, lineno, line):
		line = line.strip()
		if len(line) == 0 or line[0] == "#" or line[0] == ";":
			return
		tmp = line.split("=", 1)
		if len(tmp) != 2:
			self._log.error("Syntax error in file %s, line %d"
					% (path, lineno))
			return
		option, value = tmp
		option = option.strip()
		if len(option) == 0:
			self._log.error("Syntax error in file %s, line %d"
					% (path, lineno))
			return
		value = value.strip()
		self.write_sysctl(option, value, ignore_missing = True)

	@staticmethod
	def _get_sysctl_path(option):
		return "/proc/sys/%s" % option.replace(".", "/")

	def read_sysctl(self, option):
		path = self._get_sysctl_path(option)
		try:
			content = self._file_handler.read(path)
			content = content.strip()
			lines = content.split("\n")
			if len(lines) > 1:
				self._log.error("Failed to read sysctl parameter '%s', multi-line values are unsupported"
						% option)
				return None
			value = lines[0].strip()
			self._log.debug("Value of sysctl parameter '%s' is '%s'"
					% (option, value))
			return value
		except (OSError, IOError) as e:
			if e.errno == errno.ENOENT:
				self._log.error("Failed to read sysctl parameter '%s', the parameter does not exist"
						% option)
			else:
				self._log.error("Failed to read sysctl parameter '%s': %s"
						% (option, str(e)))
			return None

	def write_sysctl(self, option, value, ignore_missing = False):
		path = self._get_sysctl_path(option)
		if os.path.basename(path) in DEPRECATED_SYSCTL_OPTIONS:
			self._log.error("Refusing to set deprecated sysctl option %s"
					% option)
			return False
		try:
			self._log.debug("Setting sysctl parameter '%s' to '%s'"
					% (option, value))
			self._file_handler.write(path, value)
			return True
		except (OSError, IOError) as e:
			if e.errno == errno.ENOENT:
				log_func = self._log.debug if ignore_missing else self._log.error
				log_func("Failed to set sysctl parameter '%s' to '%s', the parameter does not exist"
						% (option, value))
			else:
				self._log.error("Failed to set sysctl parameter '%s' to '%s': %s"
						% (option, value, str(e)))
			return False
