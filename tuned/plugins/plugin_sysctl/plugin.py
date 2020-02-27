from tuned.plugins import base
from tuned.plugins.decorators import *
import tuned.logs
from subprocess import *
from tuned.utils.commands import commands
import tuned.consts as consts
import errno
import os
from tuned.utils.file import FileHandler

log = tuned.logs.get()

DEPRECATED_SYSCTL_OPTIONS = [ "base_reachable_time", "retrans_time" ]
SYSCTL_CONFIG_DIRS = [ "/run/sysctl.d",
		"/etc/sysctl.d" ]

class SysctlPlugin(base.Plugin):
	"""
	Plugin for applying custom sysctl options.
	"""

	def __init__(self, *args, **kwargs):
		super(SysctlPlugin, self).__init__(*args, **kwargs)
		self._has_dynamic_options = True
		self._cmd = commands()
		file_handler = FileHandler(log_func=log.debug)
		self._lib = SysctlLib(file_handler, os.listdir, log)

	def _instance_init(self, instance):
		instance._has_dynamic_tuning = False
		instance._has_static_tuning = True

		# FIXME: do we want to do this here?
		# recover original values in case of crash
		storage_key = self._storage_key(instance.name)
		instance._sysctl_original = self._storage.get(storage_key, {})
		if len(instance._sysctl_original) > 0:
			log.info("recovering old sysctl settings from previous run")
			self._instance_unapply_static(instance)
			instance._sysctl_original = {}
			self._storage.unset(storage_key)

		instance._sysctl = instance.options

	def _instance_cleanup(self, instance):
		storage_key = self._storage_key(instance.name)
		self._storage.unset(storage_key)

	def _instance_apply_static(self, instance):
		for option, value in list(instance._sysctl.items()):
			original_value = self._lib.read_sysctl(option)
			if original_value is None:
				log.error("sysctl option %s will not be set, failed to read the original value."
						% option)
			else:
				new_value = self._variables.expand(
						self._cmd.unquote(value))
				new_value = self._process_assignment_modifiers(
						new_value, original_value)
				if new_value is not None:
					instance._sysctl_original[option] = original_value
					self._lib.write_sysctl(option, new_value)

		storage_key = self._storage_key(instance.name)
		self._storage.set(storage_key, instance._sysctl_original)

		if self._global_cfg.get_bool(consts.CFG_REAPPLY_SYSCTL, consts.CFG_DEF_REAPPLY_SYSCTL):
			log.info("reapplying system sysctl")
			self._lib.apply_system_sysctl()

	def _instance_verify_static(self, instance, ignore_missing, devices):
		ret = True
		# override, so always skip missing
		ignore_missing = True
		for option, value in list(instance._sysctl.items()):
			curr_val = self._lib.read_sysctl(option)
			value = self._process_assignment_modifiers(self._variables.expand(value), curr_val)
			if value is not None:
				if self._verify_value(option, self._cmd.remove_ws(value), self._cmd.remove_ws(curr_val), ignore_missing) == False:
					ret = False
		return ret

	def _instance_unapply_static(self, instance, full_rollback = False):
		for option, value in list(instance._sysctl_original.items()):
			self._lib.write_sysctl(option, value)


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
