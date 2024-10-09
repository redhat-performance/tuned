from . import base
from .decorators import *
import tuned.logs
from . import exceptions
from tuned.utils.commands import commands
import tuned.consts as consts

import os
import re

log = tuned.logs.get()

class SystemdPlugin(base.Plugin):
	"""
	Plug-in for tuning systemd options.

	The [option]`cpu_affinity` option allows setting CPUAffinity in
	`/etc/systemd/system.conf`. This configures the CPU affinity for the
	service manager as well as the default CPU affinity for all forked
	off processes. The option takes a comma-separated list of CPUs with
	optional CPU ranges specified by the minus sign (`-`).

	.Set the CPUAffinity for `systemd` to `0 1 2 3`
	====
	----
	[systemd]
	cpu_affinity=0-3
	----
	====

	NOTE: These tunings are unloaded only on profile change followed by a reboot.
	"""

	def __init__(self, *args, **kwargs):
		if not os.path.isfile(consts.SYSTEMD_SYSTEM_CONF_FILE):
			raise exceptions.NotSupportedPluginException("Required systemd '%s' configuration file not found, disabling plugin." % consts.SYSTEMD_SYSTEM_CONF_FILE)
		super(SystemdPlugin, self).__init__(*args, **kwargs)
		self._cmd = commands()

	def _instance_init(self, instance):
		instance._has_dynamic_tuning = False
		instance._has_static_tuning = True

	def _instance_cleanup(self, instance):
		pass

	@classmethod
	def _get_config_options(cls):
		return {
			"cpu_affinity": None,
		}

	def _get_keyval(self, conf, key):
		if conf is not None:
			mo = re.search(r"^\s*" + key + r"\s*=\s*(.*)$", conf, flags = re.MULTILINE)
			if mo is not None and mo.lastindex == 1:
				return mo.group(1)
		return None

	# add/replace key with the value
	def _add_keyval(self, conf, key, val):
		(conf_new, nsubs) = re.subn(r"^(\s*" + key + r"\s*=).*$", r"\g<1>" + str(val), conf, flags = re.MULTILINE)
		if nsubs < 1:
			try:
				if conf[-1] != "\n":
					conf += "\n"
			except IndexError:
				pass
			conf += key + "=" + str(val) + "\n"
			return conf
		return conf_new

	def _del_key(self, conf, key):
		return re.sub(r"^\s*" + key + r"\s*=.*\n", "", conf, flags = re.MULTILINE)

	def _read_systemd_system_conf(self):
		systemd_system_conf = self._cmd.read_file(consts.SYSTEMD_SYSTEM_CONF_FILE, err_ret = None)
		if systemd_system_conf is None:
			log.error("error reading systemd configuration file")
			return None
		return systemd_system_conf

	def _write_systemd_system_conf(self, conf):
		tmpfile = consts.SYSTEMD_SYSTEM_CONF_FILE + consts.TMP_FILE_SUFFIX
		if not self._cmd.write_to_file(tmpfile, conf):
			log.error("error writing systemd configuration file")
			self._cmd.unlink(tmpfile, no_error = True)
			return False
		# Atomic replace, this doesn't work on Windows (AFAIK there is no way on Windows how to do this
		# atomically), but it's unlikely this code will run there
		if not self._cmd.rename(tmpfile, consts.SYSTEMD_SYSTEM_CONF_FILE):
			log.error("error replacing systemd configuration file '%s'" % consts.SYSTEMD_SYSTEM_CONF_FILE)
			self._cmd.unlink(tmpfile, no_error = True)
			return False
		return True

	def _get_storage_filename(self):
		return os.path.join(consts.PERSISTENT_STORAGE_DIR, self.name)

	def _remove_systemd_tuning(self):
		conf = self._read_systemd_system_conf()
		if (conf is not None):
			fname = self._get_storage_filename()
			cpu_affinity_saved = self._cmd.read_file(fname, err_ret = None, no_error = True)
			self._cmd.unlink(fname)
			if cpu_affinity_saved is None:
				conf = self._del_key(conf, consts.SYSTEMD_CPUAFFINITY_VAR)
			else:
				conf = self._add_keyval(conf, consts.SYSTEMD_CPUAFFINITY_VAR, cpu_affinity_saved)
			self._write_systemd_system_conf(conf)

	def _instance_unapply_static(self, instance, rollback = consts.ROLLBACK_SOFT):
		if rollback == consts.ROLLBACK_FULL:
			log.info("removing '%s' systemd tuning previously added by TuneD" % consts.SYSTEMD_CPUAFFINITY_VAR)
			self._remove_systemd_tuning()
			log.console("you may need to manualy run 'dracut -f' to update the systemd configuration in initrd image")

	# convert cpulist from systemd syntax to TuneD syntax and unpack it
	def _cpulist_convert_unpack(self, cpulist):
		if cpulist is None:
			return ""
		return " ".join(str(v) for v in self._cmd.cpulist_unpack(re.sub(r"\s+", r",", re.sub(r",\s+", r",", cpulist))))

	@command_custom("cpu_affinity", per_device = False)
	def _cmdline(self, enabling, value, verify, ignore_missing):
		conf_affinity = None
		conf_affinity_unpacked = None
		v = self._cmd.unescape(self._variables.expand(self._cmd.unquote(value)))
		v_unpacked = " ".join(str(v) for v in self._cmd.cpulist_unpack(v))
		conf = self._read_systemd_system_conf()
		if conf is not None:
			conf_affinity = self._get_keyval(conf, consts.SYSTEMD_CPUAFFINITY_VAR)
			conf_affinity_unpacked = self._cpulist_convert_unpack(conf_affinity)
		if verify:
			return self._verify_value("cpu_affinity", v_unpacked, conf_affinity_unpacked, ignore_missing)
		if enabling:
			fname = self._get_storage_filename()
			cpu_affinity_saved = self._cmd.read_file(fname, err_ret = None, no_error = True)
			if conf_affinity is not None and cpu_affinity_saved is None and v_unpacked != conf_affinity_unpacked:
				self._cmd.write_to_file(fname, conf_affinity, makedir = True)

			log.info("setting '%s' to '%s' in the '%s'" % (consts.SYSTEMD_CPUAFFINITY_VAR, v_unpacked, consts.SYSTEMD_SYSTEM_CONF_FILE))
			self._write_systemd_system_conf(self._add_keyval(conf, consts.SYSTEMD_CPUAFFINITY_VAR, v_unpacked))
