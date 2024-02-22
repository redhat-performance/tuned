from . import base
from .decorators import *
import tuned.logs
from tuned.utils.commands import commands
import os
import errno
import re

log = tuned.logs.get()

class VideoPlugin(base.Plugin):
	"""
	`video`::
	
	Sets various powersave levels on video cards. Currently, only the
	Radeon cards are supported. The powersave level can be specified
	by using the [option]`radeon_powersave` option. Supported values are:
	+
	--
	* `default`
	* `auto`
	* `low`
	* `mid`
	* `high`
	* `dynpm`
	* `dpm-battery`
	* `dpm-balanced`
	* `dpm-perfomance`
	--
	+
	For additional detail, see
	link:https://www.x.org/wiki/RadeonFeature/#kmspowermanagementoptions[KMS Power Management Options].
	+
	NOTE: This plug-in is experimental and the option might change in future releases.
	+
	.To set the powersave level for the Radeon video card to high
	====
	----
	[video]
	radeon_powersave=high
	----
	====
	"""

	def _init_devices(self):
		self._devices_supported = True
		self._free_devices = set()
		self._assigned_devices = set()

		# FIXME: this is a blind shot, needs testing
		for device in self._hardware_inventory.get_devices("drm").match_sys_name("card*").match_property("DEVTYPE", "drm_minor"):
			self._free_devices.add(device.sys_name)

		self._cmd = commands()

	def _get_device_objects(self, devices):
		return [self._hardware_inventory.get_device("drm", x) for x in devices]

	@classmethod
	def _get_config_options(self):
		return {
			"radeon_powersave" : None,
		}

	def _instance_init(self, instance):
		instance._has_dynamic_tuning = False
		instance._has_static_tuning = True

	def _instance_cleanup(self, instance):
		pass

	def _files(self, device):
		return {
			"method" : "/sys/class/drm/%s/device/power_method" % device,
			"profile": "/sys/class/drm/%s/device/power_profile" % device,
			"dpm_state": "/sys/class/drm/%s/device/power_dpm_state" % device
		}

	@command_set("radeon_powersave", per_device=True)
	def _set_radeon_powersave(self, value, device, sim, remove):
		sys_files = self._files(device)
		va = str(re.sub(r"(\s*:\s*)|(\s+)|(\s*;\s*)|(\s*,\s*)", " ", value)).split()
		if not os.path.exists(sys_files["method"]):
			if not sim:
				log.debug("radeon_powersave is not supported on '%s'" % device)
				return None
		for v in va:
			if v in ["default", "auto", "low", "mid", "high"]:
				if not sim:
					if (self._cmd.write_to_file(sys_files["method"], "profile", \
						no_error = [errno.ENOENT] if remove else False) and
						self._cmd.write_to_file(sys_files["profile"], v, \
							no_error = [errno.ENOENT] if remove else False)):
								return v
			elif v == "dynpm":
				if not sim:
					if (self._cmd.write_to_file(sys_files["method"], "dynpm", \
						no_error = [errno.ENOENT] if remove else False)):
							return "dynpm"
			# new DPM profiles, recommended to use if supported
			elif v in ["dpm-battery", "dpm-balanced", "dpm-performance"]:
				if not sim:
					state = v[len("dpm-"):]
					if (self._cmd.write_to_file(sys_files["method"], "dpm", \
						no_error = [errno.ENOENT] if remove else False) and
						self._cmd.write_to_file(sys_files["dpm_state"], state, \
							no_error = [errno.ENOENT] if remove else False)):
								return v
			else:
				if not sim:
					log.warn("Invalid option for radeon_powersave.")
				return None
		return None

	@command_get("radeon_powersave")
	def _get_radeon_powersave(self, device, ignore_missing = False):
		sys_files = self._files(device)
		if not os.path.exists(sys_files["method"]):
			log.debug("radeon_powersave is not supported on '%s'" % device)
			return None
		method = self._cmd.read_file(sys_files["method"], no_error=ignore_missing).strip()
		if method == "profile":
			return self._cmd.read_file(sys_files["profile"]).strip()
		elif method == "dynpm":
			return method
		elif method == "dpm":
			return "dpm-" + self._cmd.read_file(sys_files["dpm_state"]).strip()
		else:
			return None
