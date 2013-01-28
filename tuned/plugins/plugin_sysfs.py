import base
import re
import os.path
from decorators import *
import tuned.logs
from subprocess import *
import tuned.utils.commands

log = tuned.logs.get()

class SysfsPlugin(base.Plugin):
	"""
	Plugin for applying custom sysfs options, using specific plugins is preferred.
	"""

	# TODO: resolve possible conflicts with sysctl settings from other plugins

	def __init__(self, *args, **kwargs):
		super(self.__class__, self).__init__(*args, **kwargs)
		self._has_dynamic_options = True

	def _instance_init(self, instance):
		instance._has_dynamic_tuning = False
		instance._has_static_tuning = True

		instance._sysfs = dict(map(lambda (key, value): (os.path.normpath(key), value), instance.options.items()))
		instance._sysfs_original = {}

	def _instance_cleanup(self, instance):
		pass

	def _instance_apply_static(self, instance):
		for key, value in instance._sysfs.iteritems():
			if self._check_sysfs(key):
				instance._sysfs_original[key] = self._read_sysfs(key)
				self._write_sysfs(key, value)
			else:
				log.error("rejecting write to '%s' (not inside /sys)" % key)

	def _instance_unapply_static(self, instance):
		for key, value in instance._sysfs_original.iteritems():
			self._write_sysfs(key, value)

	def _check_sysfs(self, sysfs_file):
		return re.match(r"^/sys/.*", sysfs_file)

	def _read_sysfs(self, sysfs_file):
		data = tuned.utils.commands.read_file(sysfs_file)
		if len(data) > 0:
			return tuned.utils.commands.get_active_option(data, False)
		else:
			return None

	def _write_sysfs(self, sysfs_file, value):
		return tuned.utils.commands.write_to_file(sysfs_file, value)
