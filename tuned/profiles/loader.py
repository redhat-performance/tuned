import tuned.profiles.profile
import ConfigParser
import os.path
import collections

from tuned.profiles.exceptions import InvalidProfileException

class Loader(object):
	"""
	Profiles loader.
	"""

	__slots__ = ["_load_directories", "_profile_merger", "_profile_factory"]

	def __init__(self, load_directories, profile_factory, profile_merger):
		if type(load_directories) is not list:
			raise TypeError("load_directories parameter is not a list")

		self._load_directories = load_directories
		self._profile_factory = profile_factory
		self._profile_merger = profile_merger

	def _create_profile(self, profile_name, config):
		return tuned.profiles.profile.Profile(profile_name, config)

	@property
	def load_directories(self):
		return self._load_directories

	def load(self, profile_names):
		if type(profile_names) is str:
			readable_name = profile_names
			profile_names = [profile_names]
		else:
			readable_name = ",".join(profile_names)

		profiles = []
		processed_files = []
		self._load_profile(profile_names, profiles, processed_files)

		if len(profiles) > 1:
			final_profile = self._profile_merger.merge(profiles)
		else:
			final_profile = profiles[0]

		final_profile.name = readable_name
		return final_profile

	def _load_profile(self, profile_names, profiles, processed_files):
		for name in profile_names:
			filename = self._find_config_file(name, processed_files)
			if filename is None:
				raise InvalidProfileException("Cannot find profile '%s'." % name)
			processed_files.append(filename)

			config = self._load_config_data(filename)
			profile = self._profile_factory.create(name, config)
			if "include" in profile.options:
				include_name = profile.options.pop("include")
				self._load_profile([include_name], profiles, processed_files)

			profiles.append(profile)

	def _find_config_file(self, profile_name, skip_files=None):
		for dir_name in reversed(self._load_directories):
			config_file = os.path.join(dir_name, profile_name, "tuned.conf")
			config_file = os.path.normpath(config_file)

			if skip_files is not None and config_file in skip_files:
				continue

			if os.path.exists(config_file):
				return config_file

	def _load_config_data(self, file_name):
		parser = ConfigParser.SafeConfigParser(allow_no_value=True)
		try:
			parser.read(file_name)
		except ConfigParser.Error as e:
			raise InvalidProfileException("Cannot parse '%s'." % file_name, e)

		config = collections.OrderedDict()
		for section in parser.sections():
			config[section] = collections.OrderedDict()
			for option, value in parser.items(section):
				config[section][option] = value

		# TODO: HACK, this needs to be solved in a better way (better config parser)
		for unit_name in config:
			if config[unit_name].get("type", None) == "script" and "script" in config[unit_name]:
				dir_name = os.path.dirname(file_name)
				script_path = os.path.join(dir_name, config[unit_name]["script"])
				config[unit_name]["script"] = os.path.normpath(script_path)

		return config
