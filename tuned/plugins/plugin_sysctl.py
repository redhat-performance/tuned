import tuned.plugins
import tuned.logs
import tuned.monitors
import os
import struct
from subprocess import *

log = tuned.logs.get()

class SysctlPlugin(tuned.plugins.Plugin):
	"""
	"""

	def __init__(self, devices, options):
		"""
		"""
		super(self.__class__, self).__init__(None, options)
		self._options = options
		self._latency = None
		self._updated = False
		self._sysctl_original = {}

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
		for key, value in self._options.iteritems():
			returncode, out, err = self._exec_sysctl(key)
			if not returncode and len(out.split('=')) == 2:
				k = out.split('=')[0].strip()
				v = out.split('=')[1].strip()
				self._sysctl_original[k] = v

			self._exec_sysctl(key + "=" + value, True)
		return True

	def _revert_sysctl(self):
		for key, value in self._sysctl_original.iteritems():
			self._exec_sysctl(key + "=" + value, True)

	def cleanup(self):
		self._revert_sysctl()
		os.close(self._cpu_latency_fd)

	def update_tuning(self):
		if self._updated:
			return

		self._updated = True
		self._apply_sysctl()


