from . import base
from .decorators import *
import tuned.logs
from tuned.utils.commands import commands
import glob
import errno

log = tuned.logs.get()

class USBPlugin(base.Plugin):
	"""
	Sets autosuspend timeout of USB devices to the value specified by the
	[option]`autosuspend` option in seconds. If the [option]`devices`
	option is specified, the [option]`autosuspend` option applies to only
	the USB devices specified, otherwise it applies to all USB devices.

	The value `0` means that autosuspend is disabled.

	.Turn off USB autosuspend for USB devices `1-1` and `1-2`
	====
	----
	[usb]
	devices=1-1,1-2
	autosuspend=0
	----
	====
	"""

	def _init_devices(self):
		self._devices_supported = True
		self._free_devices = set()
		self._assigned_devices = set()

		for device in self._hardware_inventory.get_devices("usb").match_property("DEVTYPE", "usb_device"):
			self._free_devices.add(device.sys_name)

		self._cmd = commands()

	def _get_device_objects(self, devices):
		return [self._hardware_inventory.get_device("usb", x) for x in devices]

	@classmethod
	def _get_config_options(self):
		return {
			"autosuspend" : None,
		}

	def _instance_init(self, instance):
		instance._has_static_tuning = True
		instance._has_dynamic_tuning = False

	def _instance_cleanup(self, instance):
		pass

	def _autosuspend_sysfile(self, device):
		return "/sys/bus/usb/devices/%s/power/autosuspend" % device

	@command_set("autosuspend", per_device=True)
	def _set_autosuspend(self, value, device, sim, remove):
		enable = self._option_bool(value)
		if enable is None:
			return None

		val = "1" if enable else "0"
		if not sim:
			sys_file = self._autosuspend_sysfile(device)
			self._cmd.write_to_file(sys_file, val, \
				no_error = [errno.ENOENT] if remove else False)
		return val

	@command_get("autosuspend")
	def _get_autosuspend(self, device, ignore_missing=False):
		sys_file = self._autosuspend_sysfile(device)
		return self._cmd.read_file(sys_file, no_error=ignore_missing).strip()
