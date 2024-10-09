from . import base
from . import exceptions
import tuned.logs
from tuned.utils.commands import commands
import os

log = tuned.logs.get()

class EeePCSHEPlugin(base.Plugin):
	"""
	Dynamically sets the front-side bus (FSB) speed according to the
	CPU load. This feature can be found on some netbooks and is also
	known as the Asus Super Hybrid Engine. If the CPU load is lower or
	equal to the value specified by the [option]`load_threshold_powersave`
	option, the plug-in sets the FSB speed to the value specified by the
	[option]`she_powersave` option. If the CPU load is higher or
	equal to the value specified by the [option]`load_threshold_normal`
	option, it sets the FSB speed to the value specified by the
	[option]`she_normal` option. Static tuning is not supported and the
	plug-in is transparently disabled if the hardware support for this
	feature is not detected.
	
	NOTE: For details about the FSB frequencies and corresponding values, see
	link:https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-platform-eeepc-laptop[the kernel documentation].
	The provided defaults should work for most users.
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
		instance._load_monitor = None

	def _instance_cleanup(self, instance):
		if instance._load_monitor is not None:
			self._monitors_repository.delete(instance._load_monitor)
			instance._load_monitor = None

	def _instance_init_dynamic(self, instance):
		super(EeePCSHEPlugin, self)._instance_init_dynamic(instance)
		instance._load_monitor = self._monitors_repository.create("load", None)

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
