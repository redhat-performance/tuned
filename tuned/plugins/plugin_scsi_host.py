import errno
from . import hotplug
from .decorators import *
import tuned.logs
import tuned.consts as consts
from tuned.utils.commands import commands
import os
import re

log = tuned.logs.get()

class SCSIHostPlugin(hotplug.Plugin):
	"""
	Tunes options for SCSI hosts.

	The plug-in sets Aggressive Link Power Management (ALPM) to the value specified
	by the [option]`alpm` option. The option takes one of four values:
	`min_power`, `med_power_with_dipm`, `medium_power` and `max_performance`.

	NOTE: ALPM is only available on SATA controllers that use the Advanced
	Host Controller Interface (AHCI).

	.ALPM setting when extended periods of idle time are expected
	====
	----
	[scsi_host]
	alpm=med_power_with_dipm
	----
	====
	"""

	def __init__(self, *args, **kwargs):
		super(SCSIHostPlugin, self).__init__(*args, **kwargs)

		self._cmd = commands()

	def _init_devices(self):
		super(SCSIHostPlugin, self)._init_devices()
		self._devices_supported = True
		self._free_devices = set()
		for device in self._hardware_inventory.get_devices("scsi"):
			if self._device_is_supported(device):
				self._free_devices.add(device.sys_name)

		self._assigned_devices = set()

	def _get_device_objects(self, devices):
		return [self._hardware_inventory.get_device("scsi", x) for x in devices]

	@classmethod
	def _device_is_supported(cls, device):
		return  device.device_type == "scsi_host"

	def _hardware_events_init(self):
		self._hardware_inventory.subscribe(self, "scsi", self._hardware_events_callback)

	def _hardware_events_cleanup(self):
		self._hardware_inventory.unsubscribe(self)

	def _hardware_events_callback(self, event, device):
		if self._device_is_supported(device):
			super(SCSIHostPlugin, self)._hardware_events_callback(event, device)

	def _added_device_apply_tuning(self, instance, device_name):
		super(SCSIHostPlugin, self)._added_device_apply_tuning(instance, device_name)

	def _removed_device_unapply_tuning(self, instance, device_name):
		super(SCSIHostPlugin, self)._removed_device_unapply_tuning(instance, device_name)

	@classmethod
	def _get_config_options(cls):
		return {
			"alpm"               : None,
		}

	def _instance_init(self, instance):
		instance._has_static_tuning = True
		instance._has_dynamic_tuning = False

	def _instance_cleanup(self, instance):
		pass

	def _get_alpm_policy_file(self, device):
		return os.path.join("/sys/class/scsi_host/", str(device), "link_power_management_policy")

	def _get_ahci_port_cmd_file(self, device):
		return os.path.join("/sys/class/scsi_host/", str(device), "ahci_port_cmd")

	def _is_external_sata_port(self, device):
		port_cmd_file = self._get_ahci_port_cmd_file(device)
		if not os.path.isfile(port_cmd_file):
			return False
		port_cmd = int(self._cmd.read_file(port_cmd_file), 16)
		# Bit 18 is HPCP (Hot Plug Capable Port)
		# Bit 21 is ESP (External SATA Port)
		return port_cmd & (1 << 18 | 1 << 21) != 0

	@command_set("alpm", per_device = True)
	def _set_alpm(self, policy, device, instance, sim, remove):
		if policy is None:
			return None
		if self._is_external_sata_port(device):
			# According to the SATA AHCI specification, external (or hot-plug capable)
			# SATA ports must have power management disabled to reliably detect hot plug removal.
			log.info("Device '%s' is an external SATA controller, skipping ALPM setting to support hot plug" % str(device))
			return None
		policy_file = self._get_alpm_policy_file(device)
		if not sim:
			if os.path.exists(policy_file):
				self._cmd.write_to_file(policy_file, policy, \
					no_error = [errno.ENOENT] if remove else False)
			else:
				log.info("ALPM control file ('%s') not found, skipping ALPM setting for '%s'" % (policy_file, str(device)))
				return None
		return policy

	@command_get("alpm")
	def _get_alpm(self, device, instance, ignore_missing=False):
		policy_file = self._get_alpm_policy_file(device)
		policy = self._cmd.read_file(policy_file, no_error = True).strip()
		return policy if policy != "" else None
