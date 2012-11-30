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

	@classmethod
	def tunable_devices(self):
		return ["vm"]

	def _post_init(self):
		self._dynamic_tuning = False

	@classmethod
	def _get_default_options(cls):
		return {
			"transparent_hugepages" : None,
		}

	@classmethod
	def _thp_file(self):
		return "/sys/kernel/mm/redhat_transparent_hugepage/enabled"

	@command_set("transparent_hugepages")
	def _set_transparent_hugepages(self, value):
		if value not in ["always", "never"]:
			log.warn("Incorrect transparent_hugepages value.")
			return

		sys_file = VMPlugin._thp_file()
		if not os.path.exists(sys_file):
			return

		tuned.utils.commands.write_to_file(sys_file, value)

	@command_get("transparent_hugepages")
	def _get_transparent_hugepages(self):
		sys_file = VMPlugin._thp_file()
		if not os.path.exists(sys_file):
			return None
		return tuned.utils.commands.get_active_option(tuned.utils.commands.read_file(sys_file))
