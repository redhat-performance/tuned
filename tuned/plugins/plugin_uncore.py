from . import hotplug
from .decorators import *
import tuned.logs
from tuned.utils.commands import commands

import os
import fnmatch

log = tuned.logs.get()
cmd = commands()

SYSFS_DIR = "/sys/devices/system/cpu/intel_uncore_frequency/"

IS_MIN = 0
IS_MAX = 1

class UncorePlugin(hotplug.Plugin):
	"""
	An Intel-specific plug-in for limiting the maximum and minimum uncore frequency.

	The options [option]`max_freq_khz`, [option]`min_freq_khz` correspond to
	`sysfs` files exposed by Intel uncore frequency driver. Their values can be
	specified in kHz or as a percentage of their configurable range.

	.Limiting maximum uncore frequency
	====
	----
	[uncore10]
	type=uncore
	devices=uncore10
	max_freq_khz=4000000

	[uncore_all]
	type=uncore
	max_freq_khz=90%
	----
	Using this options *TuneD* will limit maximum frequency of all uncore units
	on the Intel system to 90% of the allowable range. Except uncore10 which
	maximum frequency limit will be set to 4 GHz.
	====
	"""

	def _init_devices(self):
		self._devices_supported = True
		self._assigned_devices = set()
		self._free_devices = set()
		self._is_tpmi = False

		try:
			devices = os.listdir(SYSFS_DIR)
		except OSError:
			return

		# For new TPMI interface use only uncore devices
		tpmi_devices = fnmatch.filter(devices, 'uncore*')
		if len(tpmi_devices) > 0:
			self._is_tpmi = True  # Not used at present but can be usefull in future
			devices = tpmi_devices

		for d in devices:
			self._free_devices.add(d)

		log.debug("devices: %s", str(self._free_devices))

	def _instance_init(self, instance):
		instance._has_static_tuning = True
		instance._has_dynamic_tuning = False

	def _instance_cleanup(self, instance):
		pass

	def _get(self, dev_dir, file):
		sysfs_file = SYSFS_DIR + dev_dir + "/" + file
		value = cmd.read_file(sysfs_file)
		if len(value) > 0:
			return int(value)
		return None

	def _set(self, dev_dir, file, value):
		sysfs_file = SYSFS_DIR + dev_dir + "/" + file
		if cmd.write_to_file(sysfs_file, "%u" % value):
			return value
		return None

	def _get_all(self, device):
		try:
			initial_max_freq_khz = self._get(device, "initial_max_freq_khz")
			initial_min_freq_khz = self._get(device, "initial_min_freq_khz")
			max_freq_khz = self._get(device, "max_freq_khz")
			min_freq_khz = self._get(device, "min_freq_khz")
		except (OSError, IOError):
			log.error("fail to read uncore frequency values")
			return None
		return (initial_max_freq_khz, initial_min_freq_khz, max_freq_khz, min_freq_khz)

	@classmethod
	def _get_config_options(cls):
		return {
			"max_freq_khz": None,
			"min_freq_khz": None,
		}

	def _validate_khz_value(self, device, min_or_max, value):
		try:
			freq_khz = int(value)
		except ValueError:
			log.error("value '%s' is not integer" % value)
			return None

		values = self._get_all(device)
		if values is None:
			return None
		(initial_max_freq_khz, initial_min_freq_khz, max_freq_khz, min_freq_khz) = values

		if min_or_max == IS_MAX:
			if freq_khz < min_freq_khz:
				log.error("%s: max_freq_khz %d value below min_freq_khz %d" % (device, freq_khz, min_freq_khz))
				return None

			if freq_khz > initial_max_freq_khz:
				log.info("%s: max_freq_khz %d value above initial_max_freq_khz - capped to %d" % (device, freq_khz, initial_max_freq_khz))
				freq_khz = initial_max_freq_khz

		elif min_or_max == IS_MIN:
			if freq_khz > max_freq_khz:
				log.error("%s: min_freq_khz %d value above max_freq_khz %d" % (device, freq_khz, max_freq_khz))
				return None

			if freq_khz < initial_min_freq_khz:
				log.info("%s: min_freq_khz %d value below initial_max_freq_khz - capped to %d" % (device, freq_khz, initial_min_freq_khz))
				freq_khz = initial_min_freq_khz

		else:
			return None

		return freq_khz

	def _validate_percent_value(self, value):
		try:
			pct = int(value)
		except ValueError:
			log.error("value '%s' is not integer" % value)
			return None

		if pct < 0 or pct > 100:
			log.error("percent value '%s' is not within [0..100] range" % value)
			return None

		return pct

	def _validate_value(self, device, min_or_max, value):
		if isinstance(value, str) and value[-1] == "%":
			pct = self._validate_percent_value(value.rstrip("%"))
			if pct is None:
				return None

			values = self._get_all(device)
			if values is None:
				return None
			(initial_max_freq_khz, initial_min_freq_khz, _, _) = values

			khz = initial_min_freq_khz + int(pct * (initial_max_freq_khz - initial_min_freq_khz) / 100)
		else:
			khz = value

		return self._validate_khz_value(device, min_or_max, khz)

	@command_set("max_freq_khz", per_device = True)
	def _set_max_freq_khz(self, value, device, sim, remove):
		max_freq_khz = self._validate_value(device, IS_MAX, value)
		if max_freq_khz is None:
			return None

		if sim:
			return max_freq_khz

		log.debug("%s: set max_freq_khz %d" % (device, max_freq_khz))
		return self._set(device, "max_freq_khz", max_freq_khz)

	@command_get("max_freq_khz")
	def _get_max_freq_khz(self, device, ignore_missing=False):
		if ignore_missing and not os.path.isdir(SYSFS_DIR):
			return None

		try:
			max_freq_khz = self._get(device, "max_freq_khz")
		except (OSError, IOError):
			log.error("fail to read uncore frequency values")
			return None

		log.debug("%s: get max_freq_khz %d" % (device, max_freq_khz))
		return max_freq_khz

	@command_set("min_freq_khz", per_device = True)
	def _set_min_freq_khz(self, value, device, sim, remove):
		min_freq_khz = self._validate_value(device, IS_MIN, value)
		if min_freq_khz is None:
			return None

		if sim:
			return min_freq_khz

		log.debug("%s: set min_freq_khz %d" % (device, min_freq_khz))
		return self._set(device, "min_freq_khz", min_freq_khz)

	@command_get("min_freq_khz")
	def _get_min_freq_khz(self, device, ignore_missing=False):
		if ignore_missing and not os.path.isdir(SYSFS_DIR):
			return None

		try:
			min_freq_khz = self._get(device, "min_freq_khz")
		except (OSError, IOError):
			log.error("fail to read uncore frequency values")
			return None

		log.debug("%s: get min_freq_khz %d" % (device, min_freq_khz))
		return min_freq_khz
