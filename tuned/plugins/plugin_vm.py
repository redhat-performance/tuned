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
	Enables or disables transparent huge pages depending on value of the
	[option]`transparent_hugepages` option. The option can have one of three
	possible values `always`, `madvise` and `never`.

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
		}

	def _instance_init(self, instance):
		instance._has_static_tuning = True
		instance._has_dynamic_tuning = False

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
	def _set_transparent_hugepages(self, value, sim, remove):
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
	def _set_transparent_hugepage(self, value, sim, remove):
		self._set_transparent_hugepages(value, sim, remove)

	@command_get("transparent_hugepages")
	def _get_transparent_hugepages(self):
		sys_file = os.path.join(self._thp_path(), "enabled")
		if os.path.exists(sys_file):
			return cmd.get_active_option(cmd.read_file(sys_file))
		else:
			return None

        # just an alias to transparent_hugepages
	@command_get("transparent_hugepage")
	def _get_transparent_hugepage(self):
		return self._get_transparent_hugepages()

	@command_set("transparent_hugepage.defrag")
	def _set_transparent_hugepage_defrag(self, value, sim, remove):
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
	def _get_transparent_hugepage_defrag(self):
		sys_file = os.path.join(self._thp_path(), "defrag")
		if os.path.exists(sys_file):
			return cmd.get_active_option(cmd.read_file(sys_file))
		else:
			return None
