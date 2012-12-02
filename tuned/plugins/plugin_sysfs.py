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
	def _post_init(self):
		self._dynamic_tuning = False
		self._sysfs_original = {}
		self._sysfs = self._options

		_sysfs = {}
		for key, value in self._sysfs.iteritems():
			_sysfs[os.path.normpath(key)] = value
		self._sysfs = _sysfs
		for key, value in self._sysfs.iteritems():
			self._sysfs_original[key] = self._read_sysfs(key)

	@classmethod
	def tunable_devices(self):
		return ["sysfs"]

	@classmethod
	def _get_default_options(cls):
		return {}

	def _check_sysfs(self, sysfs_file):
		if not re.match(r"^/sys/.*", sysfs_file):
			log.error("rejecting access to '%s', it doesn't seem to be sysfs tuning" % sysfs_file)
			return False
		return True

	def _read_sysfs(self, sysfs_file):
		value = None
		if self._check_sysfs(sysfs_file):
			data = tuned.utils.commands.read_file(sysfs_file)
			if len(data):
				value = tuned.utils.commands.get_active_option(data, False)
		return value

	def _write_sysfs(self, sysfs_file, value):
		if self._check_sysfs(sysfs_file):
			return tuned.utils.commands.write_to_file(sysfs_file, value)
		return False

	def _apply_sysfs(self):
		for key, value in self._sysfs.iteritems():
			self._write_sysfs(key, value)
		return True

	def _revert_sysfs(self):
		for key, value in self._sysfs_original.iteritems():
			self._write_sysfs(key, value)

	def cleanup_commands(self):
		self._revert_sysfs()

	def execute_commands(self):
		self._apply_sysfs()
