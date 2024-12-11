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
	Sets various kernel parameters at runtime.

	This plug-in is used for applying custom `sysctl` settings and should
	only be used to change system settings that are not covered by other
	*TuneD* plug-ins. If the settings are covered by other *TuneD* plug-ins,
	use those plug-ins instead.

	The syntax for this plug-in is
	`_key_=_value_`, where
	`_key_` is the same as the key name provided by the
	`sysctl` utility.

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
		for option, value in list(instance._sysctl.items()):
			original_value = self._read_sysctl(option)
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
					self._write_sysctl(option, new_value)

		storage_key = self._storage_key(instance.name)
		self._storage.set(storage_key, instance._sysctl_original)

		if self._global_cfg.get_bool(consts.CFG_REAPPLY_SYSCTL, consts.CFG_DEF_REAPPLY_SYSCTL):
			log.info("reapplying system sysctl")
			self._apply_system_sysctl(instance._sysctl)

	def _instance_verify_static(self, instance, ignore_missing, devices):
		ret = True
		# override, so always skip missing
		ignore_missing = True
		for option, value in list(instance._sysctl.items()):
			curr_val = self._read_sysctl(option)
			value = self._process_assignment_modifiers(self._variables.expand(value), curr_val)
			if value is not None:
				if self._verify_value(option, self._cmd.remove_ws(value), self._cmd.remove_ws(curr_val), ignore_missing) == False:
					ret = False
		return ret

	def _instance_unapply_static(self, instance, rollback = consts.ROLLBACK_SOFT):
		for option, value in list(instance._sysctl_original.items()):
			self._write_sysctl(option, value)

	def _apply_system_sysctl(self, instance_sysctl):
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
			self._apply_sysctl_config_file(path, instance_sysctl)
		self._apply_sysctl_config_file("/etc/sysctl.conf", instance_sysctl)

	def _apply_sysctl_config_file(self, path, instance_sysctl):
		log.debug("Applying sysctl settings from file %s" % path)
		try:
			with open(path, "r") as f:
				for lineno, line in enumerate(f, 1):
					self._apply_sysctl_config_line(path, lineno, line, instance_sysctl)
			log.debug("Finished applying sysctl settings from file %s"
					% path)
		except (OSError, IOError) as e:
			if e.errno != errno.ENOENT:
				log.error("Error reading sysctl settings from file %s: %s"
						% (path, str(e)))

	def _apply_sysctl_config_line(self, path, lineno, line, instance_sysctl):
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
		value = value.strip()
		if option in instance_sysctl:
			instance_value = self._variables.expand(instance_sysctl[option])
			if instance_value != value:
				log.info("Overriding sysctl parameter '%s' from '%s' to '%s'"
						% (option, instance_value, value))
		self._write_sysctl(option, value, ignore_missing = True)

	def _get_sysctl_path(self, option):
		# The sysctl name in sysctl tool and in /proc/sys differs.
		# All dots (.) in sysctl name are represented by /proc/sys
		# directories and all slashes in the name (/) are converted
		# to dots (.) in the /proc/sys filenames.
		return "/proc/sys/%s" % self._cmd.tr(option, "./", "/.")

	def _read_sysctl(self, option):
		path = self._get_sysctl_path(option)
		content = self._cmd.read_file(path, err_ret=None)
		if content is None:
			return None
		content = content.strip()
		if len(content.split("\n")) > 1:
			log.error("Failed to read sysctl parameter '%s', multi-line values are unsupported" % option)
			return None
		return content

	def _write_sysctl(self, option, value, ignore_missing = False):
		path = self._get_sysctl_path(option)
		if os.path.basename(path) in DEPRECATED_SYSCTL_OPTIONS:
			log.error("Refusing to set deprecated sysctl option %s" % option)
			return False
		return self._cmd.write_to_file(path, value, no_error=[errno.ENOENT] if ignore_missing else False, ignore_same=True)
