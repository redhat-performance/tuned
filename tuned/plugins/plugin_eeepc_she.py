from . import base
from . import exceptions
import tuned.logs
from tuned.utils.commands import commands
import os

log = tuned.logs.get()

class EeePCSHEPlugin(base.Plugin):
	"""
	Plugin for tuning FSB (front side bus) speed on Asus EEE PCs with SHE (Super Hybrid Engine) support.
	"""

	def __init__(self, *args, **kwargs):
		self._cmd = commands()
		self._control_file = "/sys/devices/platform/eeepc/cpufv"
		if not os.path.isfile(self._control_file):
			self._control_file = "/sys/devices/platform/eeepc-wmi/cpufv"
		if not os.path.isfile(self._control_file):
			raise exceptions.NotSupportedPluginException("Plugin is not supported on your hardware.")
		super(EeePCSHEPlugin, self).__init__(*args, **kwargs)

	@classmethod
	def _get_config_options(self):
		return {
			"load_threshold_normal"    : 0.6,
			"load_threshold_powersave" : 0.4,
			"she_powersave"            : 2,
			"she_normal"               : 1,
		}

	def _instance_init(self, instance):
		instance._has_static_tuning = False
		instance._has_dynamic_tuning = True
		instance._she_mode = None
		instance._load_monitor = self._monitors_repository.create("load", None)

	def _instance_cleanup(self, instance):
		if instance._load_monitor is not None:
			self._monitors_repository.delete(instance._load_monitor)
			instance._load_monitor = None

	def _instance_update_dynamic(self, instance, device):
		load = instance._load_monitor.get_load()["system"]
		if load <= instance.options["load_threshold_powersave"]:
			self._set_she_mode(instance, "powersave")
		elif load >= instance.options["load_threshold_normal"]:
			self._set_she_mode(instance, "normal")

	def _instance_unapply_dynamic(self, instance, device):
		# FIXME: restore previous value
		self._set_she_mode(instance, "normal")

	def _set_she_mode(self, instance, new_mode):
		new_mode_numeric = int(instance.options["she_%s" % new_mode])
		if instance._she_mode != new_mode_numeric:
			log.info("new eeepc_she mode %s (%d) " % (new_mode, new_mode_numeric))
			self._cmd.write_to_file(self._control_file, "%s" % new_mode_numeric)
			self._she_mode = new_mode_numeric
