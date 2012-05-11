import tuned.plugins
import tuned.logs
import tuned.monitors
import tuned.utils.storage
import os
import struct
import glob
from subprocess import *

log = tuned.logs.get()

class SysctlPlugin(tuned.plugins.Plugin):
	"""
	Plugin for applying custom sysctl options.
	"""

	def __init__(self, devices, options):
		"""
		"""
		super(self.__class__, self).__init__(devices, options)
		self._sysctl_original = {}
		self._sysctl = options
		del self._sysctl["_load_path"]

		# Set default sysctl from the previously running tuned2
		data = tuned.utils.storage.Storage.get_instance().data
		if data.has_key("sysctl"):
			for key, value in data["sysctl"].iteritems():
				self._exec_sysctl(key + "=" + value, True)
		tuned.utils.storage.Storage.get_instance().data["sysctl"] = {}

	@classmethod
	def _get_default_options(cls):
		return {
			"dynamic_tuning"   : "0",
		}

	def _exec_sysctl(self, data, write = False):
		if write:
			log.debug("Setting sysctl: %s" % (data))
			proc = Popen(["/sbin/sysctl", "-q", "-w", data], stdout=PIPE, stderr=PIPE)
		else:
			proc = Popen(["/sbin/sysctl", "-e", data], stdout=PIPE, stderr=PIPE)
		out, err = proc.communicate()

		if proc.returncode:
			log.error("sysctl error: %s" % (err[:-1]))
		return (proc.returncode, out, err)

	def _apply_sysctl(self):
		for key, value in self._sysctl.iteritems():
			returncode, out, err = self._exec_sysctl(key)
			if not returncode and len(out.split('=')) == 2:
				k = out.split('=')[0].strip()
				v = out.split('=')[1].strip()
				self._sysctl_original[k] = v

			self._exec_sysctl(key + "=" + value, True)

		storage = tuned.utils.storage.Storage.get_instance()
		storage.data = {"sysctl" : self._sysctl_original}
		storage.save()

		return True

	def _revert_sysctl(self):
		for key, value in self._sysctl_original.iteritems():
			self._exec_sysctl(key + "=" + value, True)

	def cleanup_commands(self):
		self._revert_sysctl()

	def execute_commands(self):
		self._apply_sysctl()

	def cleanup(self):
		pass

	def update_tuning(self):
		pass
