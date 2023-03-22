import re
from . import base
from .decorators import *
import tuned.logs
from subprocess import *
from tuned.utils.commands import commands
import tuned.consts as consts
import errno
import os

log = tuned.logs.get()

DEPRECATED_SYSCTL_OPTIONS = [ "base_reachable_time", "retrans_time" ]
SYSCTL_CONFIG_DIRS = [ "/run/sysctl.d",
		"/etc/sysctl.d" ]

class SysctlPlugin(base.Plugin):
	"""
	`sysctl`::
	
	Sets various kernel parameters at runtime.
	+
	This plug-in is used for applying custom `sysctl` settings and should
	only be used to change system settings that are not covered by other
	*TuneD* plug-ins. If the settings are covered by other *TuneD* plug-ins,
	use those plug-ins instead.
	+
	The syntax for this plug-in is
	`_key_=_value_`, where
	`_key_` is the same as the key name provided by the
	`sysctl` utility.
	+
	.Adjusting the kernel runtime kernel.sched_min_granularity_ns value
	====
	----
	[sysctl]
	kernel.sched_min_granularity_ns=3000000
	----
	====
	"""

	def __init__(self, *args, **kwargs):
		super(SysctlPlugin, self).__init__(*args, **kwargs)
		self._has_dynamic_options = True
		self._cmd = commands()

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
		system_sysctl = _read_system_sysctl()
		for option, value in list(instance._sysctl.items()):
			original_value = _read_sysctl(option)
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
					_write_sysctl(option, new_value)

		storage_key = self._storage_key(instance.name)
		self._storage.set(storage_key, instance._sysctl_original)

		if self._global_cfg.get_bool(consts.CFG_REAPPLY_SYSCTL, consts.CFG_DEF_REAPPLY_SYSCTL):
			log.info("reapplying system sysctl")
			for option, value in list(system_sysctl.items()):
				if option in instance._sysctl and instance._sysctl[option] != value:
					log.info("Overriding sysctl parameter '%s' from '%s' to '%s'"
							% (option, instance._sysctl[option], value))
				_write_sysctl(option, value, ignore_missing = True)


	def _instance_verify_static(self, instance, ignore_missing, devices):
		ret = True
		# override, so always skip missing
		ignore_missing = True
		for option, value in list(instance._sysctl.items()):
			curr_val = _read_sysctl(option)
			value = self._process_assignment_modifiers(self._variables.expand(value), curr_val)
			if value is not None:
				if self._verify_value(option, self._cmd.remove_ws(value), self._cmd.remove_ws(curr_val), ignore_missing) == False:
					ret = False
		return ret

	def _instance_unapply_static(self, instance, full_rollback = False):
		for option, value in list(instance._sysctl_original.items()):
			_write_sysctl(option, value)


def _read_system_sysctl():
	sysctls = {}
	files = {}
	for d in SYSCTL_CONFIG_DIRS:
		try:
			flist = os.listdir(d)
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
		sysctls.update(_read_sysctl_config_file(path))
	sysctls.update(_read_sysctl_config_file("/etc/sysctl.conf"))
	return sysctls

def _read_sysctl_config_file(path):
	log.debug("Reading sysctl settings from file %s" % path)
	sysctls = {}
	try:
		with open(path, "r") as f:
			for lineno, line in enumerate(f, 1):
				sysctl_line = _read_sysctl_config_line(path, lineno, line)
				if sysctl_line is not None:
					sysctls[sysctl_line[0]] = sysctl_line[1]
		log.debug("Finished reading sysctl settings from file %s"
				% path)
	except (OSError, IOError) as e:
		if e.errno != errno.ENOENT:
			log.error("Error reading sysctl settings from file %s: %s"
					% (path, str(e)))
	return sysctls

def _read_sysctl_config_line(path, lineno, line):
	line = line.strip()
	if len(line) == 0 or line[0] == "#" or line[0] == ";":
		return
	tmp = line.split("=", 1)
	if len(tmp) != 2:
		log.error("Syntax error in file %s, line %d"
				% (path, lineno))
		return
	option, value = tmp
	option = option.strip()
	if len(option) == 0:
		log.error("Syntax error in file %s, line %d"
				% (path, lineno))
		return
	return (option, value.strip())

def _get_sysctl_path(option):
	return "/proc/sys/%s" % option.replace(".", "/")

def _read_sysctl(option):
	path = _get_sysctl_path(option)
	try:
		with open(path, "r") as f:
			line = ""
			for i, line in enumerate(f):
				if i > 0:
					log.error("Failed to read sysctl parameter '%s', multi-line values are unsupported"
							% option)
					return None
			value = line.strip()
		log.debug("Value of sysctl parameter '%s' is '%s'"
				% (option, value))
		return value
	except (OSError, IOError) as e:
		if e.errno == errno.ENOENT:
			log.error("Failed to read sysctl parameter '%s', the parameter does not exist"
					% option)
		else:
			log.error("Failed to read sysctl parameter '%s': %s"
					% (option, str(e)))
		return None

def _write_sysctl(option, value, ignore_missing = False):
	path = _get_sysctl_path(option)
	if os.path.basename(path) in DEPRECATED_SYSCTL_OPTIONS:
		log.error("Refusing to set deprecated sysctl option %s"
				% option)
		return False
	try:
		log.debug("Setting sysctl parameter '%s' to '%s'"
				% (option, value))
		with open(path, "w") as f:
			f.write(value)
		return True
	except (OSError, IOError) as e:
		if e.errno == errno.ENOENT:
			log_func = log.debug if ignore_missing else log.error
			log_func("Failed to set sysctl parameter '%s' to '%s', the parameter does not exist"
					% (option, value))
		else:
			log.error("Failed to set sysctl parameter '%s' to '%s': %s"
					% (option, value, str(e)))
		return False
