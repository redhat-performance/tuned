import tuned.plugins
import tuned.logs
import tuned.monitors
import glob
import os
import struct
from subprocess import *

log = tuned.logs.get()

class ScriptPlugin(tuned.plugins.Plugin):
	"""
	Plugin for running custom scripts with profile activation and deactivation.
	"""

	def __init__(self, devices, options):
		super(self.__class__, self).__init__(devices, options)

		self._scripts = []
		if self._options["script"].startswith("/"):
			self._scripts.append(self._options["script"])
		else:
			self._scripts.append(os.path.join(self._options["_load_path"], self._options["script"]))

	@classmethod
	def _get_default_options(cls):
		return {
			"script"   : None,
			"dynamic_tuning" : "0",
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

	def cleanup(self):
		pass

	def update_tuning(self):
		pass
