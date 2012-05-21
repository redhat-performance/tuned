import base
from decorators import *
import tuned.logs
from subprocess import *

log = tuned.logs.get()

class SysctlPlugin(base.Plugin):
	"""
	Plugin for applying custom sysctl options.
	"""

	def __init__(self, *args, **kwargs):
		super(self.__class__, self).__init__(*args, **kwargs)

		self._sysctl_original = {}
		self._sysctl = self._options
		del self._sysctl["_load_path"]

		old_sysctl_options = self._storage.get("options", {})
		for key, value in old_sysctl_options.iteritems():
			self._exec_sysctl(key + "=" + value, True)
		self._storage.unset("options")
		# FIXME: do this globally
		#self._storage.save()

	@classmethod
	def _get_default_options(cls):
		return {}

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

	def cleanup(self):
		pass

	def update_tuning(self):
		pass
