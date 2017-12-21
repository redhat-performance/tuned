import tuned.profiles.profile
import tuned.profiles.variables
from configobj import ConfigObj, ConfigObjError
import tuned.consts as consts
import os.path
import collections
import tuned.logs
import re
from tuned.profiles.exceptions import InvalidProfileException

log = tuned.logs.get()

class Loader(object):
	"""
	Profiles loader.
	"""

	__slots__ = ["_profile_locator", "_profile_merger", "_profile_factory", "_global_config", "_variables"]

	def __init__(self, profile_locator, profile_factory, profile_merger, global_config, variables):
		self._profile_locator = profile_locator
		self._profile_factory = profile_factory
		self._profile_merger = profile_merger
		self._global_config = global_config
		self._variables = variables

	def _create_profile(self, profile_name, config):
		return tuned.profiles.profile.Profile(profile_name, config)

	@classmethod
	def safe_name(cls, profile_name):
		return re.match(r'^[a-zA-Z0-9_.-]+$', profile_name)

	@property
	def profile_locator(self):
		return self._profile_locator

	def load(self, profile_names):
		if type(profile_names) is not list:
			profile_names = profile_names.split()

		profile_names = list(filter(self.safe_name, profile_names))
		if len(profile_names) == 0:
			raise InvalidProfileException("No profile or invalid profiles were specified.")

		if len(profile_names) > 1:
			log.info("loading profiles: %s" % ", ".join(profile_names))
		else:
			log.info("loading profile: %s" % profile_names[0])
		profiles = []
		processed_files = []
		self._load_profile(profile_names, profiles, processed_files)

		if len(profiles) > 1:
			final_profile = self._profile_merger.merge(profiles)
		else:
			final_profile = profiles[0]

		final_profile.name = " ".join(profile_names)
		if "variables" in final_profile.units:
			self._variables.add_from_cfg(final_profile.units["variables"].options)
			del(final_profile.units["variables"])
		# FIXME hack, do all variable expansions in one place
		self._expand_vars_in_devices(final_profile)
		return final_profile

	def _expand_vars_in_devices(self, profile):
		for unit in profile.units:
			profile.units[unit].devices = self._variables.expand(profile.units[unit].devices)

	def _load_profile(self, profile_names, profiles, processed_files):
		for name in profile_names:
			filename = self._profile_locator.get_config(name, processed_files)
			if filename is None:
				raise InvalidProfileException("Cannot find profile '%s' in '%s'." % (name, list(reversed(self._profile_locator._load_directories))))
			processed_files.append(filename)

			config = self._load_config_data(filename)
			profile = self._profile_factory.create(name, config)
			if "include" in profile.options:
				include_name = self._variables.expand(profile.options.pop("include"))
				self._load_profile([include_name], profiles, processed_files)

			profiles.append(profile)

	def _expand_profile_dir(self, profile_dir, string):
		return re.sub(r'(?<!\\)\$\{i:PROFILE_DIR\}', profile_dir, string)

	def _load_config_data(self, file_name):
		try:
			config_obj = ConfigObj(file_name, raise_errors = True, list_values = False, interpolation = False)
		except ConfigObjError as e:
			raise InvalidProfileException("Cannot parse '%s'." % file_name, e)

		config = collections.OrderedDict()
		for section in list(config_obj.keys()):
			config[section] = collections.OrderedDict()
			try:
				keys = list(config_obj[section].keys())
			except AttributeError:
				raise InvalidProfileException("Error parsing section '%s' in file '%s'." % (section, file_name))
			for option in keys:
				config[section][option] = config_obj[section][option]

		dir_name = os.path.dirname(file_name)
		# TODO: Could we do this in the same place as the expansion of other functions?
		for section in config:
			for option in config[section]:
				config[section][option] = self._expand_profile_dir(dir_name, config[section][option])

		# TODO: HACK, this needs to be solved in a better way (better config parser)
		for unit_name in config:
			if "script" in config[unit_name] and config[unit_name].get("script", None) is not None:
				script_path = os.path.join(dir_name, config[unit_name]["script"])
				config[unit_name]["script"] = [os.path.normpath(script_path)]

		return config
