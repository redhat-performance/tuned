import tuned.consts as consts
from . import base
import tuned.logs
import os
from subprocess import Popen, PIPE

log = tuned.logs.get()

class ScriptPlugin(base.Plugin):
	"""
	Executes an external script or binary when the profile is loaded or
	unloaded. You can choose an arbitrary executable.

	IMPORTANT: The `script` plug-in is provided mainly for compatibility
	with earlier releases. Prefer other *TuneD* plug-ins if they cover
	the required functionality.

	*TuneD* calls the executable with one of the following arguments:

	* `start` when loading the profile
	* `stop` when unloading the profile

	You need to correctly implement the `stop` action in your executable
	and revert all settings that you changed during the `start`
	action. Otherwise, the roll-back step after changing your *TuneD*
	profile will not work.

	Bash scripts can import the [filename]`/usr/lib/tuned/functions`
	Bash library and use the functions defined there. Use these
	functions only for functionality that is not natively provided
	by *TuneD*. If a function name starts with an underscore, such as
	`_wifi_set_power_level`, consider the function private and do not
	use it in your scripts, because it might change in the future.

	Specify the path to the executable using the `script` parameter in
	the plug-in configuration.

	.Running a Bash script from a profile
	====
	To run a Bash script named `script.sh` that is located in the profile
	directory, use:
	----
	[script]
	script=${i:PROFILE_DIR}/script.sh
	----
	====
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
		ret = True
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
					ret = False
			except (OSError,IOError) as e:
				log.error("script '%s' error: %s" % (script, e))
				ret = False
		return ret

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

	def _instance_unapply_static(self, instance, rollback = consts.ROLLBACK_SOFT):
		args = ["stop"]
		if rollback == consts.ROLLBACK_FULL:
			args = args + ["full_rollback"]
		self._call_scripts(reversed(instance._scripts), args)
		super(ScriptPlugin, self)._instance_unapply_static(instance, rollback)
