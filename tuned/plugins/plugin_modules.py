import re
import os.path
from . import base
from .decorators import *
import tuned.logs
from subprocess import *
from tuned.utils.commands import commands
import tuned.consts as consts

log = tuned.logs.get()

class ModulesPlugin(base.Plugin):
	"""
	Plug-in for applying custom kernel modules options.

	This plug-in can set parameters to kernel modules. It creates
	`/etc/modprobe.d/tuned.conf` file. The syntax is
	`_module_=_option1=value1 option2=value2..._` where `_module_` is
	the module name and `_optionx=valuex_` are module options which may
	or may not be present.

	.Load module `netrom` with module parameter `nr_ndevs=2`
	====
	----
	[modules]
	netrom=nr_ndevs=2
	----
	====

	Modules can also be forced to load/reload by using an additional
	`+r` option prefix.

	.(Re)load module `netrom` with module parameter `nr_ndevs=2`
	====
	----
	[modules]
	netrom=+r nr_ndevs=2
	----
	====

	The `+r` switch will also cause *TuneD* to try and remove `netrom`
	module (if loaded) and try and (re)insert it with the specified
	parameters. The `+r` can be followed by an optional comma (`+r,`)
	for better readability.

	When using `+r` the module will be loaded immediately by the *TuneD*
	daemon itself rather than waiting for the OS to load it with the
	specified parameters.
	"""

	def __init__(self, *args, **kwargs):
		super(ModulesPlugin, self).__init__(*args, **kwargs)
		self._has_dynamic_options = True
		self._cmd = commands()

	def _instance_init(self, instance):
		instance._has_dynamic_tuning = False
		instance._has_static_tuning = True
		instance._modules = instance.options

	def _instance_cleanup(self, instance):
		pass

	def _reload_modules(self, modules):
		for module in modules:
			retcode, out = self._cmd.execute(["modprobe", "-r", module])
			if retcode < 0:
				log.warning("'modprobe' command not found, cannot reload kernel modules, reboot is required")
				return
			elif retcode > 0:
				log.debug("cannot remove kernel module '%s': %s" % (module, out.strip()))
			retcode, out = self._cmd.execute(["modprobe", module])
			if retcode != 0:
				log.warning("cannot insert/reinsert module '%s', reboot is required: %s" % (module, out.strip()))

	def _instance_apply_static(self, instance):
		self._clear_modprobe_file()
		s = ""
		retcode = 0
		skip_check = False
		reload_list = []
		for option, value in list(instance._modules.items()):
			module = self._variables.expand(option)
			v = self._variables.expand(value)
			if not skip_check:
				retcode, out = self._cmd.execute(["modinfo", module])
				if retcode < 0:
					skip_check = True
					log.warning("'modinfo' command not found, not checking kernel modules")
				elif retcode > 0:
					log.error("kernel module '%s' not found, skipping it" % module)
			if skip_check or retcode == 0:
				if len(v) > 1 and v[0:2] == "+r":
					v = re.sub(r"^\s*\+r\s*,?\s*", "", v)
					reload_list.append(module)
				if len(v) > 0:
					s += "options " + module + " " + v + "\n"
				else:
					log.debug("module '%s' doesn't have any option specified, not writing it to modprobe.d" % module)
		self._cmd.write_to_file(consts.MODULES_FILE, s)
		l = len(reload_list)
		if l > 0:
			self._reload_modules(reload_list)
			if len(instance._modules) != l:
				log.info(consts.STR_HINT_REBOOT)

	def _unquote_path(self, path):
		return str(path).replace("/", "")

	def _instance_verify_static(self, instance, ignore_missing, devices):
		ret = True
		# not all modules exports all their parameteters through sysfs, so hardcode check with ignore_missing
		ignore_missing = True
		r = re.compile(r"\s+")
		for option, value in list(instance._modules.items()):
			module = self._variables.expand(option)
			v = self._variables.expand(value)
			v = re.sub(r"^\s*\+r\s*,?\s*", "", v)
			mpath = "/sys/module/%s" % module
			if not os.path.exists(mpath):
				ret = False
				log.error(consts.STR_VERIFY_PROFILE_FAIL % "module '%s' is not loaded" % module)
			else:
				log.info(consts.STR_VERIFY_PROFILE_OK % "module '%s' is loaded" % module)
				l = r.split(v)
				for item in l:
					arg = item.split("=", 1)
					if len(arg) != 2:
						log.warning("unrecognized module option for module '%s': %s" % (module, item))
					else:
						if self._verify_value(arg[0], arg[1],
							self._cmd.read_file(mpath + "/parameters/" + self._unquote_path(arg[0]), err_ret = None, no_error = True),
							ignore_missing) == False:
								ret = False
		return ret

	def _instance_unapply_static(self, instance, rollback = consts.ROLLBACK_SOFT):
		if rollback == consts.ROLLBACK_FULL:
			self._clear_modprobe_file()

	def _clear_modprobe_file(self):
		s = self._cmd.read_file(consts.MODULES_FILE, no_error = True)
		l = s.split("\n")
		i = j = 0
		ll = len(l)
		r = re.compile(r"^\s*#")
		while i < ll:
			if r.search(l[i]) is None:
				j = i
				i = ll
			i += 1
		s = "\n".join(l[0:j])
		if len(s) > 0:
			s += "\n"
		self._cmd.write_to_file(consts.MODULES_FILE, s)
