from . import base
from .decorators import *
import os
import errno
import tuned.logs
from tuned.consts import ACPI_DIR

log = tuned.logs.get()


class ACPIPlugin(base.Plugin):
	"""
	Configures the ACPI driver.

	The only currently supported option is
	[option]`platform_profile`, which sets the ACPI
	platform profile sysfs attribute,
	a generic power/performance preference API for other drivers.
	Multiple profiles can be specified, separated by `|`.
	The first available profile is selected.

	.Selecting a platform profile
	====
	----
	[acpi]
	platform_profile=balanced|low-power
	----
	Using this option, *TuneD* will try to set the platform profile
	to `balanced`. If that fails, it will try to set it to `low-power`.
	====
	"""
	def __init__(self, *args, **kwargs):
		super(ACPIPlugin, self).__init__(*args, **kwargs)

	@classmethod
	def _get_config_options(cls):
		return {"platform_profile": None}

	def _instance_init(self, instance):
		instance._has_static_tuning = True
		instance._has_dynamic_tuning = False

	def _instance_cleanup(self, instance):
		pass

	@classmethod
	def _platform_profile_choices_path(cls):
		return os.path.join(ACPI_DIR, "platform_profile_choices")

	@classmethod
	def _platform_profile_path(cls):
		return os.path.join(ACPI_DIR, "platform_profile")

	@command_set("platform_profile")
	def _set_platform_profile(self, profiles, sim, remove):
		if not os.path.isfile(self._platform_profile_path()):
			log.debug("ACPI platform_profile is not supported on this system")
			return None
		profiles = [profile.strip() for profile in profiles.split('|')]
		avail_profiles = set(self._cmd.read_file(self._platform_profile_choices_path()).split())
		for profile in profiles:
			if profile in avail_profiles:
				if not sim:
					log.info("Setting platform_profile to '%s'" % profile)
					self._cmd.write_to_file(self._platform_profile_path(), profile, \
						no_error=[errno.ENOENT] if remove else False)
				return profile
			log.warning("Requested platform_profile '%s' unavailable" % profile)
		log.error("Failed to set platform_profile. Is the value in the profile correct?")
		return None

	@command_get("platform_profile")
	def _get_platform_profile(self, ignore_missing=False):
		if not os.path.isfile(self._platform_profile_path()):
			log.debug("ACPI platform_profile is not supported on this system")
			return None
		return self._cmd.read_file(self._platform_profile_path()).strip()
