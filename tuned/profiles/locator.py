import os

class Locator(object):
	"""
	Profiles locator and enumerator.
	"""

	__slots__ = ["_load_directories"]

	def __init__(self, load_directories):
		if type(load_directories) is not list:
			raise TypeError("load_directories parameter is not a list")
		self._load_directories = load_directories

	@property
	def load_directories(self):
		return self._load_directories

	def _get_config_filename(self, *path_parts):
		path_parts = list(path_parts) + ["tuned.conf"]
		config_name = os.path.join(*path_parts)
		return os.path.normpath(config_name)

	def get_config(self, profile_name, skip_files=None):
		for dir_name in reversed(self._load_directories):
			config_file = self._get_config_filename(dir_name, profile_name)

			if skip_files is not None and config_file in skip_files:
				continue

			if os.path.isfile(config_file):
				return config_file

		return None

	def get_known_names(self):
		profiles = set()
		for dir_name in self._load_directories:
			try:
				for profile_name in os.listdir(dir_name):
					config_file = self._get_config_filename(dir_name, profile_name)
					if os.path.isfile(config_file):
						profiles.add(profile_name)
			except OSError:
				pass

		return sorted(list(profiles))
