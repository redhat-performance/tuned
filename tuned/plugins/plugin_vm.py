import base
from decorators import *
import tuned.logs

import os
import struct
import glob

log = tuned.logs.get()

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
	def _set_transparent_hugepages(self, value):
		if value not in ["always", "never"]:
			log.warn("Incorrect 'transparent_hugepages' value.")
			return

		sys_file = self._thp_file()
		if os.path.exists(sys_file):
			tuned.utils.commands.write_to_file(sys_file, value)
		else:
			log.warn("Option 'transparent_hugepages' is not supported on current hardware.")

	@command_get("transparent_hugepages")
	def _get_transparent_hugepages(self):
		sys_file = self._thp_file()
		if os.path.exists(sys_file):
			return tuned.utils.commands.get_active_option(tuned.utils.commands.read_file(sys_file))
		else:
			return None
