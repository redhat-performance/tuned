from . import base
from .decorators import *
import tuned.logs

import os
import errno
import struct
import glob
from tuned.utils.commands import commands

log = tuned.logs.get()
cmd = commands()

class VMPlugin(base.Plugin):
	"""
	Tunes selected sysctl options in `/proc/sys/vm`, currently
	[option]`dirty_ratio`, [option]`dirty_background_ratio`,
	[option]`dirty_bytes`, and [option]`dirty_background_bytes`.
	See https://docs.kernel.org/admin-guide/sysctl/vm.html for detailed
	documentation of these options.

	Additionaly enables or disables transparent huge pages depending on
	the value of the [option]`transparent_hugepages` option. The option
	can have one of three possible values: `always`, `madvise` and `never`.

	.Disable transparent hugepages
	====
	----
	[vm]
	transparent_hugepages=never
	----
	====

	The [option]`transparent_hugepage.defrag` option specifies the
	defragmentation policy. Possible values for this option are `always`,
	`defer`, `defer+madvise`, `madvise` and `never`. For a detailed
	explanation of these values refer to
	link:https://www.kernel.org/doc/Documentation/vm/transhuge.txt[Transparent Hugepage Support].
	"""

	@classmethod
	def _get_config_options(self):
		return {
			"transparent_hugepages" : None,
			"transparent_hugepage" : None,
			"transparent_hugepage.defrag" : None,
			"dirty_bytes" : None,
			"dirty_ratio" : None,
			"dirty_background_bytes" : None,
			"dirty_background_ratio" : None
		}

	@staticmethod
	def _check_conflicting_dirty_options(instance, first, second):
		if instance.options[first] is not None and instance.options[second] is not None:
			log.warning("Conflicting options '%s' and '%s', this may cause undefined behavior." % (first, second))

	@staticmethod
	def _proc_sys_vm_option_path(option):
		return os.path.join("/proc/sys/vm", option)

	def _instance_init(self, instance):
		instance._has_static_tuning = True
		instance._has_dynamic_tuning = False
		self._check_conflicting_dirty_options(instance, "dirty_bytes", "dirty_ratio")
		self._check_conflicting_dirty_options(instance, "dirty_background_bytes", "dirty_background_ratio")

	def _instance_cleanup(self, instance):
		pass

	@classmethod
	def _thp_path(self):
		path = "/sys/kernel/mm/transparent_hugepage"
		if not os.path.exists(path):
			# RHEL-6 support
			path =  "/sys/kernel/mm/redhat_transparent_hugepage"
		return path

	@command_set("transparent_hugepages")
	def _set_transparent_hugepages(self, value, instance, sim, remove):
		if value not in ["always", "never", "madvise"]:
			if not sim:
				log.warning("Incorrect 'transparent_hugepages' value '%s'." % str(value))
			return None

		cmdline = cmd.read_file("/proc/cmdline", no_error = True)
		if cmdline.find("transparent_hugepage=") > 0:
			if not sim:
				log.info("transparent_hugepage is already set in kernel boot cmdline, ignoring value from profile")
			return None

		sys_file = os.path.join(self._thp_path(), "enabled")
		if os.path.exists(sys_file):
			if not sim:
				cmd.write_to_file(sys_file, value, \
					no_error = [errno.ENOENT] if remove else False)
			return value
		else:
			if not sim:
				log.warning("Option 'transparent_hugepages' is not supported on current hardware.")
			return None

        # just an alias to transparent_hugepages
	@command_set("transparent_hugepage")
	def _set_transparent_hugepage(self, value, instance, sim, remove):
		self._set_transparent_hugepages(value, instance, sim, remove)

	@command_get("transparent_hugepages")
	def _get_transparent_hugepages(self, instance):
		sys_file = os.path.join(self._thp_path(), "enabled")
		if os.path.exists(sys_file):
			return cmd.get_active_option(cmd.read_file(sys_file))
		else:
			return None

        # just an alias to transparent_hugepages
	@command_get("transparent_hugepage")
	def _get_transparent_hugepage(self, instance):
		return self._get_transparent_hugepages(instance)

	@command_set("transparent_hugepage.defrag")
	def _set_transparent_hugepage_defrag(self, value, instance, sim, remove):
		sys_file = os.path.join(self._thp_path(), "defrag")
		if os.path.exists(sys_file):
			if not sim:
				cmd.write_to_file(sys_file, value, \
					no_error = [errno.ENOENT] if remove else False)
			return value
		else:
			if not sim:
				log.warning("Option 'transparent_hugepage.defrag' is not supported on current hardware.")
			return None

	@command_get("transparent_hugepage.defrag")
	def _get_transparent_hugepage_defrag(self, instance):
		sys_file = os.path.join(self._thp_path(), "defrag")
		if os.path.exists(sys_file):
			return cmd.get_active_option(cmd.read_file(sys_file))
		else:
			return None

	def _check_twice_pagesize(self, option, int_value):
		min_bytes = 2 * int(cmd.getconf("PAGESIZE"))
		if int_value < min_bytes:
			log.error("The value of '%s' must be at least twice the page size (%s)." % (option, min_bytes))
			return False
		return True

	def _check_positive(self, option, int_value):
		if int_value <= 0:
			log.error("The value of '%s' must be positive." % option)
			return False
		return True

	def _check_ratio(self, option, int_value):
		if not 0 <= int_value <= 100:
			log.error("The value of '%s' must be between 0 and 100." % option)
			return False
		return True

	@command_custom("dirty_bytes")
	def _dirty_bytes(self, enabling, value, verify, ignore_missing, instance):
		if value is not None and value.strip().endswith("%"):
			return self._dirty_option("dirty_ratio", "dirty_bytes", self._check_ratio, enabling, value.strip().rstrip("%"), verify)
		return self._dirty_option("dirty_bytes", "dirty_ratio", self._check_twice_pagesize, enabling, value, verify)

	@command_custom("dirty_ratio")
	def _dirty_ratio(self, enabling, value, verify, ignore_missing, instance):
		log.warning("The 'dirty_ratio' option is deprecated and does not support inheritance, use 'dirty_bytes' with '%' instead.")
		return self._dirty_option("dirty_ratio", "dirty_bytes", self._check_ratio, enabling, value, verify)

	@command_custom("dirty_background_bytes")
	def _dirty_background_bytes(self, enabling, value, verify, ignore_missing, instance):
		if value is not None and value.strip().endswith("%"):
			return self._dirty_option("dirty_background_ratio", "dirty_background_bytes", self._check_ratio, enabling, value.strip().rstrip("%"), verify)
		return self._dirty_option("dirty_background_bytes", "dirty_background_ratio", self._check_positive, enabling, value, verify)

	@command_custom("dirty_background_ratio")
	def _dirty_background_ratio(self, enabling, value, verify, ignore_missing, instance):
		log.warning("The 'dirty_background_ratio' option is deprecated and does not support inheritance, use 'dirty_background_bytes' with '%' instead.")
		return self._dirty_option("dirty_background_ratio", "dirty_background_bytes", self._check_ratio, enabling, value, verify)

	def _dirty_option(self, option, counterpart, check_fun, enabling, value, verify):
		option_path = self._proc_sys_vm_option_path(option)
		counterpart_path = self._proc_sys_vm_option_path(counterpart)
		option_key = self._storage_key(command_name=option)
		counterpart_key = self._storage_key(command_name=counterpart)
		if not os.path.isfile(option_path):
			log.warning("Option '%s' is not supported on the current hardware." % option)
		current_value = cmd.read_file(option_path).strip()
		if verify:
			return current_value == value
		if enabling:
			try:
				int_value = int(value)
			except ValueError:
				log.error("The value of '%s' must be an integer." % option)
				return None
			if not check_fun(option, int_value):
				return None
			if current_value == value:
				log.info("Not setting option '%s' to '%s', already set." % (option, value))
				return value
			# Backup: if the option (e.g. dirty_bytes) is currently 0,
			# its counterpart (dirty_ratio) is the active one, so we
			# back up that one instead.
			if int(current_value) == 0:
				current_counterpart_value = cmd.read_file(counterpart_path).strip()
				self._storage.set(counterpart_key, current_counterpart_value)
			else:
				self._storage.set(option_key, current_value)
			log.info("Setting option '%s' to '%s'." % (option, value))
			cmd.write_to_file(option_path, value)
			return value
		# Rollback is analogous to the backup: if there is no backed up
		# value for this option, it means that its counterpart was active
		# and we have to restore that one.
		old_value = self._storage.get(option_key)
		old_counterpart_value = self._storage.get(counterpart_key)
		if old_value is not None:
			log.info("Setting option '%s' to '%s'" % (option, old_value))
			cmd.write_to_file(option_path, old_value)
		elif old_counterpart_value is not None:
			log.info("Setting option '%s' to '%s'" % (counterpart, old_counterpart_value))
			cmd.write_to_file(counterpart_path, old_counterpart_value)
		else:
			log.info("Not restoring '%s', previous value is the same or unknown." % option)
		return None
