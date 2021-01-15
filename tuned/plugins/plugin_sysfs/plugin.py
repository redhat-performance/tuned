from tuned.plugins import base
import glob
import re
import os.path
from tuned.plugins.decorators import *
import tuned.logs
from subprocess import *
from tuned.utils.commands import commands

log = tuned.logs.get()

class SysfsPlugin(base.Plugin):
	"""
	Plugin for applying custom sysfs options, using specific plugins is preferred.
	"""

	# TODO: resolve possible conflicts with sysctl settings from other plugins

	def __init__(self, *args, **kwargs):
		super(SysfsPlugin, self).__init__(*args, **kwargs)
		self._has_dynamic_options = True
		self._cmd = commands()

	def _instance_init(self, instance):
		instance._has_dynamic_tuning = False
		instance._has_static_tuning = True

		instance._sysfs = dict([(os.path.normpath(key_value[0]), key_value[1]) for key_value in list(instance.options.items())])
		instance._sysfs_original = {}

	def _instance_cleanup(self, instance):
		pass

	def _instance_apply_static(self, instance):
		for key, value in list(instance._sysfs.items()):
			v = self._variables.expand(value)
			for f in glob.iglob(key):
				if self._check_sysfs(f):
					instance._sysfs_original[f] = self._read_sysfs(f)
					self._write_sysfs(f, v)
				else:
					log.error("rejecting write to '%s' (not inside /sys)" % f)

	def _instance_verify_static(self, instance, ignore_missing, devices):
		ret = True
		for key, value in list(instance._sysfs.items()):
			v = self._variables.expand(value)
			for f in glob.iglob(key):
				if self._check_sysfs(f):
					curr_val = self._read_sysfs(f)
					if self._verify_value(f, v, curr_val, ignore_missing) == False:
						ret = False
		return ret

	def _instance_unapply_static(self, instance, full_rollback = False):
		for key, value in list(instance._sysfs_original.items()):
			self._write_sysfs(key, value)

	def _check_sysfs(self, sysfs_file):
		return re.match(r"^/sys/.*", sysfs_file)

	def _read_sysfs(self, sysfs_file):
		data = self._cmd.read_file(sysfs_file).strip()
		if len(data) > 0:
			return self._cmd.get_active_option(data, False)
		else:
			return None

	def _write_sysfs(self, sysfs_file, value):
		return self._cmd.write_to_file(sysfs_file, value)
