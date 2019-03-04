import tuned.consts as consts
from . import base
import tuned.logs
import os
from subprocess import Popen, PIPE

log = tuned.logs.get()

class ScriptPlugin(base.Plugin):
	"""
	Plugin for running custom scripts with profile activation and deactivation.
	"""

	@classmethod
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

	def _call_scripts(self, scripts, arguments):
		for script in scripts:
			environ = os.environ
			environ.update(self._variables.get_env())
			log.info("calling script '%s' with arguments '%s'" % (script, str(arguments)))
			log.debug("using environment '%s'" % str(list(environ.items())))
			try:
				proc = Popen([script] +  arguments, \
						stdout=PIPE, stderr=PIPE, \
						close_fds=True, env=environ, \
						universal_newlines = True, \
						cwd = os.path.dirname(script))
				out, err = proc.communicate()
				if len(err):
					log.error("script '%s' error output: '%s'" % (script, err[:-1]))
				if proc.returncode:
					log.error("script '%s' returned error code: %d" % (script, proc.returncode))
					return False
			except (OSError,IOError) as e:
				log.error("script '%s' error: %s" % (script, e))
				return False
		return True

	def _instance_apply_static(self, instance):
		super(ScriptPlugin, self)._instance_apply_static(instance)
		self._call_scripts(instance._scripts, ["start"])

	def _instance_verify_static(self, instance, ignore_missing, devices):
		ret = True
		if super(ScriptPlugin, self)._instance_verify_static(instance,
				ignore_missing, devices) == False:
			ret = False
		args = ["verify"]
		if ignore_missing:
			args += ["ignore_missing"]
		if self._call_scripts(instance._scripts, args) == True:
			log.info(consts.STR_VERIFY_PROFILE_OK % instance._scripts)
		else:
			log.error(consts.STR_VERIFY_PROFILE_FAIL % instance._scripts)
			ret = False
		return ret

	def _instance_unapply_static(self, instance, full_rollback = False):
		args = ["stop"]
		if full_rollback:
			args = args + ["full_rollback"]
		self._call_scripts(reversed(instance._scripts), args)
		super(ScriptPlugin, self)._instance_unapply_static(instance, full_rollback)
