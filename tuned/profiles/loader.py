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

	def load(self, profile_names):
		configs = []
		processed_files = []
		if type(profile_names) is str:
			profile_names = [profile_names]

		readable_name = ",".join

		while len(profile_names) > 0:
			name = profile_names.pop(0)
			filename = self._find_config_file(name, processed_files)
			if filename is None:
				raise InvalidProfileException("Cannot find profile '%s'." % name)
			processed_files.append(filename)

			config = self._load_config_data(filename)

			if "main" in config and config["main"].get("include", None) is not None:
				profile_names.insert(0, config["main"]["include"])
				del config["main"]["include"]

			configs.insert(0, config)

		if len(configs) == 1:
			final_config = configs[0]
		else:
			final_config = self._merger.merge(configs)

		return self._create_profile(readable_name, final_config)

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
			raise InvalidProfileException("Cannot load profile.", e)

		data = {}
		for section in parser.sections():
			data[section] = {}
			for option, value in parser.items(section):
				data[section][option] = value

		self._clean_config_data(data, file_name)
		return data

	def _clean_config_data(self, config, file_name):
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
