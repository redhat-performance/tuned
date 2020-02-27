from tuned.plugins import base
from tuned.plugins.decorators import *
import tuned.logs
from subprocess import *
from tuned.utils.commands import commands
import tuned.consts as consts
import os
from tuned.utils.file import FileHandler
from .library import SysctlLib

log = tuned.logs.get()

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
