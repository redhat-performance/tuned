import os
import base
from decorators import *
import tuned.logs
import tuned.utils.commands

log = tuned.logs.get()

class SelinuxPlugin(base.Plugin):
	"""
	Plugin for tuning SELinux options.
	"""

	@classmethod
	def _get_selinux_path(self):
		path = "/sys/fs/selinux"
		if not os.path.exists(path):
			path = "/selinux"
			if not os.path.exists(path):
				path = None
		return path

	def __init__(self, *args, **kwargs):
		self._selinux_path = self._get_selinux_path()
		if self._selinux_path is None:
			raise exceptions.NotSupportedPluginException("SELinux is not enabled on your system or incompatible version is used.")
		self._cache_threshold_path = os.path.join(self._selinux_path, "avc", "cache_threshold")
		super(self.__class__, self).__init__(*args, **kwargs)

	def _get_config_options(self):
		return {
			"avc_cache_threshold" : None,
		}

	def _instance_init(self, instance):
		instance._has_static_tuning = True
		instance._has_dynamic_tuning = False

	def _instance_cleanup(self, instance):
		pass

	@command_set("avc_cache_threshold")
	def _set_avc_cache_threshold(self, value):
		if value is None:
			return
		threshold = int(value)
		if threshold >= 0:
			tuned.utils.commands.write_to_file(self._cache_threshold_path, threshold)

	@command_get("avc_cache_threshold")
	def _get_avc_cache_threshold(self):
		value = tuned.utils.commands.read_file(self._cache_threshold_path)
		if len(value) > 0:
			return int(value)
		return None
