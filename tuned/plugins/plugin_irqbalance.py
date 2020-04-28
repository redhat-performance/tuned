from . import base
from .decorators import command_custom
from tuned import consts
import tuned.logs
import errno
import perf
import re

log = tuned.logs.get()

class IrqbalancePlugin(base.Plugin):
	"""
	Plugin for irqbalance settings management.
	"""

	def __init__(self, *args, **kwargs):
		super(IrqbalancePlugin, self).__init__(*args, **kwargs)
		self._cpus = perf.cpu_map()

	def _instance_init(self, instance):
		instance._has_dynamic_tuning = False
		instance._has_static_tuning = True

	def _instance_cleanup(self, instance):
		pass

	@classmethod
	def _get_config_options(cls):
		return {
			"banned_cpus": None,
		}

	def _read_irqbalance_sysconfig(self):
		try:
			with open(consts.IRQBALANCE_SYSCONFIG_FILE, "r") as f:
				return f.read()
		except IOError as e:
			if e.errno == errno.ENOENT:
				log.warn("irqbalance sysconfig file is missing. Is irqbalance installed?")
			else:
				log.error("Failed to read irqbalance sysconfig file: %s" % e)
			return None

	def _write_irqbalance_sysconfig(self, content):
		try:
			with open(consts.IRQBALANCE_SYSCONFIG_FILE, "w") as f:
				f.write(content)
			return True
		except IOError as e:
			log.error("Failed to write irqbalance sysconfig file: %s" % e)
			return False

	def _write_banned_cpus(self, sysconfig, banned_cpumask):
		return sysconfig + "IRQBALANCE_BANNED_CPUS=%s\n" % banned_cpumask

	def _clear_banned_cpus(self, sysconfig):
		lines = []
		for line in sysconfig.split("\n"):
			if not re.match(r"\s*IRQBALANCE_BANNED_CPUS=", line):
				lines.append(line)
		return "\n".join(lines)

	def _restart_irqbalance(self):
		# Exit code 5 means unit not found (see 'EXIT_NOTINSTALLED' in
		# systemd.exec(5))
		retcode, out = self._cmd.execute(
			["systemctl", "try-restart", "irqbalance"],
			no_errors=[5])
		if retcode != 0:
			log.warn("Failed to restart irqbalance. Is it installed?")

	def _set_banned_cpus(self, banned_cpumask):
		content = self._read_irqbalance_sysconfig()
		if content is None:
			return
		content = self._clear_banned_cpus(content)
		content = self._write_banned_cpus(content, banned_cpumask)
		if self._write_irqbalance_sysconfig(content):
			self._restart_irqbalance()

	def _restore_banned_cpus(self):
		content = self._read_irqbalance_sysconfig()
		if content is None:
			return
		content = self._clear_banned_cpus(content)
		if self._write_irqbalance_sysconfig(content):
			self._restart_irqbalance()

	@command_custom("banned_cpus", per_device=False)
	def _banned_cpus(self, enabling, value, verify, ignore_missing):
		banned_cpumask = None
		if value is not None:
			banned = set(self._cmd.cpulist_unpack(value))
			present = set(self._cpus)
			if banned.issubset(present):
				banned_cpumask = self._cmd.cpulist2hex(list(banned))
			else:
				str_cpus = ",".join([str(x) for x in self._cpus])
				log.error("Invalid banned_cpus specified, '%s' does not match available cores '%s'"
					  % (value, str_cpus))

		if (enabling or verify) and banned_cpumask is None:
			return None
		if verify:
			# Verification is currently not supported
			return None
		elif enabling:
			self._set_banned_cpus(banned_cpumask)
		else:
			self._restore_banned_cpus()
