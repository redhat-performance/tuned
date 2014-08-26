import base
import tuned.logs
import os
from subprocess import Popen, PIPE

log = tuned.logs.get()

class ScriptPlugin(base.Plugin):
	"""
	Plugin for running custom scripts with profile activation and deactivation.
	"""

	def _get_config_options(self):
		return {
			"script" : None,
		}

	def _instance_init(self, instance):
		instance._has_static_tuning = True
		instance._has_dynamic_tuning = False
		if instance.options["script"] is not None:
			# FIXME: this hack originated from profiles merger
			assert isinstance(instance.options["script"], list)
			instance._scripts = instance.options["script"]
		else:
			instance._scripts = []

	def _instance_cleanup(self, instance):
		pass

	def _call_scripts(self, scripts, argument):
		for script in scripts:
			log.info("calling script '%s' with argument '%s'" % (script, argument))
			try:
				proc = Popen([script, argument], stdout=PIPE, stderr=PIPE, close_fds=True)
				out, err = proc.communicate()
				if proc.returncode:
					log.error("script '%s' error: %s" % (script, err[:-1]))
			except (OSError,IOError) as e:
				log.error("script '%s' error: %s" % (script, e))

	def _instance_apply_static(self, instance):
		super(self.__class__, self)._instance_apply_static(instance)
		self._call_scripts(instance._scripts, "start")

	def _instance_unapply_static(self, instance):
		self._call_scripts(reversed(instance._scripts), "stop")
		super(self.__class__, self)._instance_unapply_static(instance)
