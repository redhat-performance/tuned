import tuned.profiles.profile
import ConfigParser
import os.path

from tuned.profiles.exceptions import InvalidProfileException


class Loader(object):
	"""
	Profiles loader.
	"""

	__slots__ = [ "_load_directories" ]

	def __init__(self, load_directories = None):
		if load_directories is None:
			load_directories = [ "/var/lib/tuned", "/etc/tuned" ]
		elif type(load_directories) is not list:
			raise TypeError("load_directories parameter is not a list")

		self._load_directories = load_directories

	def _create_profile(self, profile_name, config):
		return tuned.profiles.profile.Profile(profile_name, config)

	@property
	def load_directories(self):
		return self._load_directories

	def add_directory(self, new_dir):
		self._load_directories.append(new_dir)

	def load(self, profile_name):
		file_name = self._find_config(profile_name)
		if file_name is None:
			raise InvalidProfileException("Profile '%s' not found." % profile_name)

		config = self._load_config(file_name)
		self._clean_config(config, file_name)

		# merging is removed temporarily

		return self._create_profile(profile_name, config)

	def _find_config(self, profile_name, skip_files=None):
		for dir_name in reversed(self._load_directories):
			config_file = os.path.join(dir_name, profile_name, "tuned.conf")
			config_file = os.path.normpath(config_file)

			if skip_files is not None and config_file in skip_files:
				continue

			if os.path.exists(config_file):
				return config_file

	def _load_config(self, file_name):
		parser = ConfigParser.SafeConfigParser(allow_no_value=True)
		try:
			parser.read(file_name)
		except ConfigParser.Error as e:
			raise InvalidProfileException("Cannot load profile.", e)

		data = {}
		for section in parser.sections():
			data[section] = {}
			for option, value in parser.items(section):
				data[section][option] = value
		return data

	def _clean_config(self, config, file_name):
		for unit_name in config:
			# nothing special for global options
			if unit_name == "main":
				continue

			# no plugin type specified, assume it matches the unit name
			if not "type" in config[unit_name]:
				config[unit_name]["type"] = unit_name

			# special case: script names have to be expanded
			if config[unit_name]["type"] == "script" and "script" in config[unit_name]:
				dir_name = os.path.dirname(file_name)
				script_path = os.path.join(dir_name, config[unit_name]["script"])
				config[unit_name]["script"] = os.path.normpath(script_path)
