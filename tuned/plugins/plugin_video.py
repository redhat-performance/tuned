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
	Sets various power saving features on video cards.
	Radeon cards are supported.
	The powersave level can be specified
	by using the [option]`radeon_powersave` option. Supported values are:

	* `default`
	* `auto`
	* `low`
	* `mid`
	* `high`
	* `dynpm`
	* `dpm-battery`
	* `dpm-balanced`
	* `dpm-perfomance`

	For additional detail, see
	link:https://www.x.org/wiki/RadeonFeature/#kmspowermanagementoptions[KMS Power Management Options].

	NOTE: This plug-in is experimental and the option might change in future releases.

	.Setting powersave level for the Radeon video card to high
	====
	----
	[video]
	radeon_powersave=high
	----
	====

	Mobile hardware with amdgpu driven eDP panels can be configured
	with the [option]`panel_power_savings` option.
	This accepts a value range from 0 to 4, where 4 is the highest power savings
	but will trade off color accuracy.
	"""

	def __init__(self, *args, **kwargs):
		super(VideoPlugin, self).__init__(*args, **kwargs)

	def _init_devices(self):
		self._devices_supported = True
		self._free_devices = set()
		self._assigned_devices = set()

		# Add any radeon and amdgpu hardware with /any/ supported attributes present
		for device in self._hardware_inventory.get_devices("drm").match_sys_name("card*-*"):
			attrs = self._files(device.sys_name)
			for attr in attrs:
				if os.path.exists(attrs[attr]):
					self._free_devices.add(device.sys_name)
		self._cmd = commands()

	def _get_device_objects(self, devices):
		return [self._hardware_inventory.get_device("drm", x) for x in devices]

	@classmethod
	def _get_config_options(self):
		return {
			"radeon_powersave" : None,
			"panel_power_savings": None,
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
			"dpm_state": "/sys/class/drm/%s/device/power_dpm_state" % device,
			"panel_power_savings": "/sys/class/drm/%s/amdgpu/panel_power_savings" % device,
		}

	def apply_panel_power_saving_target(self, device, target, sim=False):
		"""Apply the target value to the panel_power_savings file if it doesn't already have it"""

		# if we don't have the file, we might be radeon not amdgpu
		if not os.path.exists(self._files(device)["panel_power_savings"]):
			return None

		# make sure the value is different (avoids unnecessary kernel modeset)
		current = int(self._get_panel_power_savings(device))
		if current == target:
			log.info(
				"panel_power_savings for %s already %s" % (device, target)
			)
			return target

		# flush it out
		log.info("%s panel_power_savings -> %s" % (device, target))
		if sim or self._cmd.write_to_file(self._files(device)["panel_power_savings"], target):
			return target
		return None

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
					log.warning("Invalid option for radeon_powersave.")
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

	@command_set("panel_power_savings", per_device=True)
	def _set_panel_power_savings(self, value, device, sim, remove):
		"""Set the panel_power_savings value"""
		try:
			value = int(value, 10)
		except ValueError:
			log.warning("Invalid value %s for panel_power_savings" % value)
			return None
		if value in range(0, 5):
			return self.apply_panel_power_saving_target(device, value, sim)
		else:
			log.warning("Invalid value %s for panel_power_savings" % value)
		return None

	@command_get("panel_power_savings")
	def _get_panel_power_savings(self, device, ignore_missing=False):
		"""Get the current panel_power_savings value"""
		if not os.path.exists(self._files(device)["panel_power_savings"]):
			log.debug("panel_power_savings is not supported on '%s'" % device)
			return None
		fname = self._files(device)["panel_power_savings"]
		return self._cmd.read_file(fname, no_error=ignore_missing).strip()
