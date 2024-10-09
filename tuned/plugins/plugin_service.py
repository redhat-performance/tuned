from . import base
import collections
import tuned.consts as consts
from .decorators import *
import os
import re
import tuned.logs
from tuned.utils.commands import commands

log = tuned.logs.get()
cmd = commands()

class Service():
	def __init__(self, start = None, enable = None, cfg_file = None, runlevel = None):
		self.enable = enable
		self.start = start
		self.cfg_file = cfg_file
		self.runlevel = runlevel

class InitHandler():
	def runlevel_get(self):
		(retcode, out) = cmd.execute(["runlevel"])
		return out.split()[-1] if retcode == 0 else None

	def daemon_reload(self):
		cmd.execute(["telinit", "q"])

	def cfg_install(self, name, cfg_file):
		pass

	def cfg_uninstall(self, name, cfg_file):
		pass

	def cfg_verify(self, name, cfg_file):
		return None

# no enable/disable
class SysVBasicHandler(InitHandler):
	def start(self, name):
		cmd.execute(["service", name, "start"])

	def stop(self, name):
		cmd.execute(["service", name, "stop"])

	def enable(self, name, runlevel):
		raise NotImplementedError()

	def disable(self, name, runlevel):
		raise NotImplementedError()

	def is_running(self, name):
		(retcode, out) = cmd.execute(["service", name, "status"], no_errors = [0])
		return retcode == 0

	def is_enabled(self, name, runlevel):
		raise NotImplementedError()

class SysVHandler(SysVBasicHandler):
	def enable(self, name, runlevel):
		cmd.execute(["chkconfig", "--level", runlevel, name, "on"])

	def disable(self, name, runlevel):
		cmd.execute(["chkconfig", "--level", runlevel, name, "off"])

	def is_enabled(self, name, runlevel):
		(retcode, out) = cmd.execute(["chkconfig", "--list", name])
		return out.split("%s:" % str(runlevel))[1][:2] == "on" if retcode == 0 else None

class SysVRCHandler(SysVBasicHandler):
	def enable(self, name, runlevel):
		cmd.execute(["sysv-rc-conf", "--level", runlevel, name, "on"])

	def disable(self, name, runlevel):
		cmd.execute(["sysv-rc-conf", "--level", runlevel, name, "off"])

	def is_enabled(self, name, runlevel):
		(retcode, out) = cmd.execute(["sysv-rc-conf", "--list", name])
		return out.split("%s:" % str(runlevel))[1][:2] == "on" if retcode == 0 else None

class OpenRCHandler(InitHandler):
	def runlevel_get(self):
		(retcode, out) = cmd.execute(["rc-status", "-r"])
		return out.strip() if retcode == 0 else None

	def start(self, name):
		cmd.execute(["rc-service", name, "start"])

	def stop(self, name):
		cmd.execute(["rc-service", name, "stop"])

	def enable(self, name, runlevel):
		cmd.execute(["rc-update", "add", name, runlevel])

	def disable(self, name, runlevel):
		cmd.execute(["rc-update", "del", name, runlevel])

	def is_running(self, name):
		(retcode, out) = cmd.execute(["rc-service", name, "status"], no_errors = [0])
		return retcode == 0

	def is_enabled(self, name, runlevel):
		(retcode, out) = cmd.execute(["rc-update", "show", runlevel])
		return bool(re.search(r"\b" + re.escape(name) + r"\b", out))

class SystemdHandler(InitHandler):
	# runlevel not used
	def runlevel_get(self):
		return ""

	def start(self, name):
		cmd.execute(["systemctl", "restart", name])

	def stop(self, name):
		cmd.execute(["systemctl", "stop", name])

	def enable(self, name, runlevel):
		cmd.execute(["systemctl", "enable", name])

	def disable(self, name, runlevel):
		cmd.execute(["systemctl", "disable", name])

	def is_running(self, name):
		(retcode, out) = cmd.execute(["systemctl", "is-active", name], no_errors = [0])
		return retcode == 0

	def is_enabled(self, name, runlevel):
		(retcode, out) = cmd.execute(["systemctl", "is-enabled", name], no_errors = [0])
		status = out.strip()
		return True if status == "enabled" else False if status =="disabled" else None

	def cfg_install(self, name, cfg_file):
		log.info("installing service configuration overlay file '%s' for service '%s'" % (cfg_file, name))
		if not os.path.exists(cfg_file):
			log.error("Unable to find service configuration '%s'" % cfg_file)
			return
		dirpath = consts.SERVICE_SYSTEMD_CFG_PATH % name
		try:
			os.makedirs(dirpath, consts.DEF_SERVICE_CFG_DIR_MODE)
		except OSError as e:
			log.error("Unable to create directory '%s': %s" % (dirpath, e))
			return
		cmd.copy(cfg_file, dirpath)
		self.daemon_reload()

	def cfg_uninstall(self, name, cfg_file):
		log.info("uninstalling service configuration overlay file '%s' for service '%s'" % (cfg_file, name))
		dirpath = consts.SERVICE_SYSTEMD_CFG_PATH % name
		path = "%s/%s" % (dirpath, os.path.basename(cfg_file))
		cmd.unlink(path)
		self.daemon_reload()
		# remove the service dir if empty, do not check for errors
		try:
			os.rmdir(dirpath)
		except (FileNotFoundError, OSError):
			pass

	def cfg_verify(self, name, cfg_file):
		if cfg_file is None:
			return None
		path = "%s/%s" % (consts.SERVICE_SYSTEMD_CFG_PATH % name, os.path.basename(cfg_file))
		if not os.path.exists(cfg_file):
			log.error("Unable to find service '%s' configuration '%s'" % (name, cfg_file))
			return False
		if not os.path.exists(path):
			log.error("Service '%s' configuration not installed in '%s'" % (name, path))
			return False
		sha256sum1 = cmd.sha256sum(cfg_file)
		sha256sum2 = cmd.sha256sum(path)
		return sha256sum1 == sha256sum2

class ServicePlugin(base.Plugin):
	"""
	Plug-in for handling sysvinit, sysv-rc, openrc and systemd services.

	The syntax is as follows:

	[subs="+quotes,+macros"]
	----
	[service]
	service.__service_name__=__commands__[,file:__file__]
	----

	Supported service-handling `_commands_` are `start`, `stop`, `enable`
	and `disable`. The optional `file:__file__` directive installs an overlay
	configuration file `__file__`. Multiple commands must be comma (`,`)
	or semicolon (`;`) separated. If the directives conflict, the last
	one is used.

	The service plugin supports configuration overlays only for systemd.
	In other init systems, this directive is ignored. The configuration
	overlay files are copied to `/etc/systemd/system/__service_name__.service.d/`
	directories. Upon profile unloading, the directory is removed if it is empty.

	With systemd, the `start` command is implemented by `restart` in order
	to allow loading of the service configuration file overlay.

	NOTE: With non-systemd init systems, the plug-in operates on the
	current runlevel only.

	.Start and enable the `sendmail` service with an overlay file
	====
	----
	[service]
	service.sendmail=start,enable,file:${i:PROFILE_DIR}/tuned-sendmail.conf
	----
	The internal variable `${i:PROFILE_DIR}` points to the directory
	from which the profile is loaded.
	====
	"""

	def __init__(self, *args, **kwargs):
		super(ServicePlugin, self).__init__(*args, **kwargs)
		self._has_dynamic_options = True
		self._init_handler = self._detect_init_system()

	def _check_cmd(self, command):
		(retcode, out) = cmd.execute(command, no_errors = [0])
		return retcode == 0

	def _detect_init_system(self):
		if self._check_cmd(["systemctl", "status"]):
			log.debug("detected systemd")
			return SystemdHandler()
		elif self._check_cmd(["chkconfig"]):
			log.debug("detected generic sysvinit")
			return SysVHandler()
		elif self._check_cmd(["update-rc.d", "-h"]):
			log.debug("detected sysv-rc")
			return SysVRCHandler()
		elif self._check_cmd(["rc-update", "-h"]):
			log.debug("detected openrc")
			return OpenRCHandler()
		else:
			raise exceptions.NotSupportedPluginException("Unable to detect your init system, disabling the plugin.")

	def _parse_service_options(self, name,  val):
		l = re.split(r"\s*[,;]\s*", val)
		service = Service()
		for i in l:
			if i == "enable":
				service.enable = True
			elif i == "disable":
				service.enable = False
			elif i == "start":
				service.start = True
			elif i == "stop":
				service.start = False
			elif i[:5] == "file:":
				service.cfg_file = i[5:]
			else:
				log.error("service '%s': invalid service option: '%s'" % (name, i))
		return service

	def _instance_init(self, instance):
		instance._has_dynamic_tuning = False
		instance._has_static_tuning = True

		self._services = collections.OrderedDict([(option[8:], self._parse_service_options(option[8:], 
			self._variables.expand(value))) for option, value in instance.options.items()
			if option[:8] == "service." and len(option) > 8])
		instance._services_original = {}

	def _instance_cleanup(self, instance):
		pass

	def _process_service(self, name, start, enable, runlevel):
		if start:
			self._init_handler.start(name)
		elif start is not None:
			self._init_handler.stop(name)
		if enable:
			self._init_handler.enable(name, runlevel)
		elif enable is not None:
			self._init_handler.disable(name, runlevel)

	def _instance_apply_static(self, instance):
		runlevel = self._init_handler.runlevel_get()
		if runlevel is None:
			log.error("Cannot detect runlevel")
			return
		
		for service in self._services.items():
			is_enabled = self._init_handler.is_enabled(service[0], runlevel)
			is_running = self._init_handler.is_running(service[0])
			instance._services_original[service[0]] = Service(is_running, is_enabled, service[1].cfg_file, runlevel)
			if service[1].cfg_file:
				self._init_handler.cfg_install(service[0], service[1].cfg_file)
			self._process_service(service[0], service[1].start, service[1].enable, runlevel)

	def _instance_verify_static(self, instance, ignore_missing, devices):
		runlevel = self._init_handler.runlevel_get()
		if runlevel is None:
			log.error(consts.STR_VERIFY_PROFILE_FAIL % "cannot detect runlevel")
			return False

		ret = True
		for service in self._services.items():
			ret_cfg_verify = self._init_handler.cfg_verify(service[0], service[1].cfg_file)
			if ret_cfg_verify:
				log.info(consts.STR_VERIFY_PROFILE_OK % "service '%s' configuration '%s' matches" % (service[0], service[1].cfg_file))
			elif ret_cfg_verify is not None:
				log.error(consts.STR_VERIFY_PROFILE_FAIL % "service '%s' configuration '%s' differs" % (service[0], service[1].cfg_file))
				ret = False
			else:
				log.info(consts.STR_VERIFY_PROFILE_VALUE_MISSING % "service '%s' configuration '%s'" % (service[0], service[1].cfg_file))
			is_enabled = self._init_handler.is_enabled(service[0], runlevel)
			is_running = self._init_handler.is_running(service[0])
			if self._verify_value("%s running" % service[0], service[1].start, is_running, ignore_missing) is False:
				ret = False
			if self._verify_value("%s enabled" % service[0], service[1].enable, is_enabled, ignore_missing) is False:
				ret = False
		return ret

	def _instance_unapply_static(self, instance, rollback = consts.ROLLBACK_SOFT):
		for name, value in list(instance._services_original.items()):
			if value.cfg_file:
				self._init_handler.cfg_uninstall(name, value.cfg_file)
			self._process_service(name, value.start, value.enable, value.runlevel)
