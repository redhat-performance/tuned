import re
import base
from decorators import *
import tuned.logs
from subprocess import *
from tuned.utils.commands import commands
import tuned.consts as consts

log = tuned.logs.get()

class SysctlPlugin(base.Plugin):
	"""
	Plugin for applying custom sysctl options.
	"""

	def __init__(self, *args, **kwargs):
		super(self.__class__, self).__init__(*args, **kwargs)
		self._has_dynamic_options = True
		self._cmd = commands()

	def _sysctl_storage_key(self, instance):
		return "%s/options" % instance.name

	def _instance_init(self, instance):
		instance._has_dynamic_tuning = False
		instance._has_static_tuning = True

		# FIXME: do we want to do this here?
		# recover original values in case of crash
		instance._sysctl_original = self._storage.get(self._sysctl_storage_key(instance), {})
		if len(instance._sysctl_original) > 0:
			log.info("recovering old sysctl settings from previous run")
			self._instance_unapply_static(instance)
			instance._sysctl_original = {}
			self._storage.unset(self._sysctl_storage_key(instance))

		instance._sysctl = instance.options

	def _instance_cleanup(self, instance):
		self._storage.unset(self._sysctl_storage_key(instance))

	def _instance_apply_static(self, instance):
		for option, value in instance._sysctl.items():
			original_value = self._read_sysctl(option)
			if original_value != None:
				instance._sysctl_original[option] = original_value
			self._write_sysctl(option, self._variables.expand(self._cmd.unquote(value)))

		self._storage.set("options", instance._sysctl_original)

		if self._global_cfg.get_bool(consts.CFG_REAPPLY_SYSCTL, consts.CFG_DEF_REAPPLY_SYSCTL):
			log.info("reapplying system sysctl")
			self._cmd.execute(["sysctl", "--system"])

	def _instance_verify_static(self, instance, ignore_missing):
		ret = True
		# override, so always skip missing
		ignore_missing = True
		for option, value in instance._sysctl.items():
			curr_val = self._read_sysctl(option)
			if self._verify_value(option, self._cmd.remove_ws(self._variables.expand(value)), curr_val, ignore_missing) == False:
				ret = False
		return ret

	def _instance_unapply_static(self, instance, full_rollback = False):
		for option, value in instance._sysctl_original.items():
			self._write_sysctl(option, value)

	def _execute_sysctl(self, arguments):
		execute = ["sysctl"] + arguments
		log.debug("executing %s" % execute)
		return self._cmd.execute(execute)

	def _read_sysctl(self, option):
		retcode, stdout = self._execute_sysctl(["-e", option])
		if retcode == 0:
			parts = map(lambda value: self._cmd.remove_ws(value), stdout.split("=", 1))
			if len(parts) == 2:
				option, value = parts
				return value
		return None

	def _write_sysctl(self, option, value):
		retcode, stdout = self._execute_sysctl(["-q", "-w", "%s=%s" % (option, value)])
		return retcode == 0
