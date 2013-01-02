import base
from decorators import *
import tuned.logs
from subprocess import *

log = tuned.logs.get()

class SysctlPlugin(base.Plugin):
	"""
	Plugin for applying custom sysctl options.
	"""

	_has_dynamic_options = True

	def _post_init(self):
		self._dynamic_tuning = False
		self._sysctl_original = {}
		self._sysctl = self._options

		old_sysctl_options = self._storage.get("options", {})
		for key, value in old_sysctl_options.iteritems():
			self._exec_sysctl(key + "=" + value, True)
		self._storage.unset("options")

	@classmethod
	def tunable_devices(self):
		return ["sysctl"]

	@classmethod
	def _get_default_options(cls):
		return {}

	def _exec_sysctl(self, data, write = False):
		if write:
			log.debug("Setting sysctl: %s" % (data))
			proc = Popen(["/sbin/sysctl", "-q", "-w", data], stdout=PIPE, stderr=PIPE, close_fds=True)
		else:
			proc = Popen(["/sbin/sysctl", "-e", data], stdout=PIPE, stderr=PIPE, close_fds=True)
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

		self._storage.set("options", self._sysctl_original)
		# FIXME: do this globally
		#self._storage.save()

		return True

	def _revert_sysctl(self):
		for key, value in self._sysctl_original.iteritems():
			self._exec_sysctl(key + "=" + value, True)

	def cleanup_commands(self):
		self._revert_sysctl()

	def execute_commands(self):
		self._apply_sysctl()
