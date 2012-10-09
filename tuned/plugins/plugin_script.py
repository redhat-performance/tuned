import base
import tuned.logs
import os
from subprocess import Popen, PIPE

log = tuned.logs.get()

class ScriptPlugin(base.Plugin):
	"""
	Plugin for running custom scripts with profile activation and deactivation.
	"""

	def _post_init(self):
		self._dynamic_tuning = False
		self._scripts = []
		if self._options["script"] is None:
			return

		if self._options["script"].startswith("/"):
			self._scripts.append(self._options["script"])
		else:
			self._scripts.append(os.path.join(self._options["_load_path"], self._options["script"]))

	@classmethod
	def _get_default_options(cls):
		return {
			"script" : None,
		}

	def _call_scripts(self, arg = "start"):
		for script in self._scripts:
			log.info("Calling script %s" % (script))
			try:
				proc = Popen([script, arg], stdout=PIPE, stderr=PIPE)
				out, err = proc.communicate()

				if proc.returncode:
					log.error("script %s error: %s" % (script, err[:-1]))
			except (OSError,IOError) as e:
				log.error("Script %s error: %s" % (script, e))
		return True

	def execute_commands(self):
		self._call_scripts()

	def cleanup_commands(self):
		self._call_scripts("stop")
