import os
from . import base
from .decorators import *
import tuned.logs
from tuned.plugins import exceptions
from tuned.utils.commands import commands

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
		self._cmd = commands()
		self._selinux_path = self._get_selinux_path()
		if self._selinux_path is None:
			raise exceptions.NotSupportedPluginException("SELinux is not enabled on your system or incompatible version is used.")
		self._cache_threshold_path = os.path.join(self._selinux_path, "avc", "cache_threshold")
		super(SelinuxPlugin, self).__init__(*args, **kwargs)

	@classmethod
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
	def _set_avc_cache_threshold(self, value, sim):
		if value is None:
			return None
		threshold = int(value)
		if threshold >= 0:
			if not sim:
				self._cmd.write_to_file(self._cache_threshold_path, threshold)
			return threshold
		else:
			return None

	@command_get("avc_cache_threshold")
	def _get_avc_cache_threshold(self):
		value = self._cmd.read_file(self._cache_threshold_path)
		if len(value) > 0:
			return int(value)
		return None
