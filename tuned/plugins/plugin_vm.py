import base
from decorators import *
import tuned.logs

import os
import struct
import glob
from tuned.utils.commands import commands

log = tuned.logs.get()
cmd = commands()

class VMPlugin(base.Plugin):
	"""
	Plugin for tuning memory management.
	"""

	def _get_config_options(self):
		return {
			"transparent_hugepages" : None,
		}

	def _instance_init(self, instance):
		instance._has_static_tuning = True
		instance._has_dynamic_tuning = False

	def _instance_cleanup(self, instance):
		pass

	@classmethod
	def _thp_file(self):
		path = "/sys/kernel/mm/transparent_hugepage/enabled"
		if not os.path.exists(path):
			path =  "/sys/kernel/mm/redhat_transparent_hugepage/enabled"
		return path

	@command_set("transparent_hugepages")
	def _set_transparent_hugepages(self, value, sim):
		if value not in ["always", "never"]:
			if not sim:
				log.warn("Incorrect 'transparent_hugepages' value.")
			return None

		sys_file = self._thp_file()
		if os.path.exists(sys_file):
			if not sim:
				cmd.write_to_file(sys_file, value)
			return value
		else:
			if not sim:
				log.warn("Option 'transparent_hugepages' is not supported on current hardware.")
			return None

	@command_get("transparent_hugepages")
	def _get_transparent_hugepages(self):
		sys_file = self._thp_file()
		if os.path.exists(sys_file):
			return cmd.get_active_option(cmd.read_file(sys_file))
		else:
			return None
