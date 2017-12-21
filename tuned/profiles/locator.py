import os
import tuned.consts as consts
from configobj import ConfigObj, ConfigObjError

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
			# basename is protection not to get out of the path
			config_file = self._get_config_filename(dir_name, os.path.basename(profile_name))

			if skip_files is not None and config_file in skip_files:
				continue

			if os.path.isfile(config_file):
				return config_file

		return None

	def check_profile_name_format(self, profile_name):
		return profile_name is not None and profile_name != "" and "/" not in profile_name

	def parse_config(self, profile_name):
		if not self.check_profile_name_format(profile_name):
			return None
		config_file = self.get_config(profile_name)
		if config_file is None:
			return None
		try:
			return ConfigObj(config_file, list_values = False, interpolation = False)
		except (IOError, OSError, ConfigObjError) as e:
			return None

	# Get profile attributes (e.g. summary, description), attrs is list of requested attributes,
	# if it is not list it is converted to list, defvals is list of default values to return if
	# attribute is not found, it is also converted to list if it is not list.
	# Returns list of the following format [status, profile_name, attr1_val, attr2_val, ...],
	# status is boolean.
	def get_profile_attrs(self, profile_name, attrs, defvals = None):
		# check types
		try:
			attrs_len = len(attrs)
		except TypeError:
			attrs = [attrs]
			attrs_len = 1
		try:
			defvals_len = len(defvals)
		except TypeError:
			defvals = [defvals]
			defvals_len = 1
		# Extend defvals if needed, last value is used for extension
		if defvals_len < attrs_len:
			defvals = defvals + ([defvals[-1]] * (attrs_len - defvals_len))
		config = self.parse_config(profile_name)
		if config is None:
			return [False, "", "", ""]
		if consts.PLUGIN_MAIN_UNIT_NAME in config:
			d = config[consts.PLUGIN_MAIN_UNIT_NAME]
		else:
			d = dict()
		vals = [True, profile_name]
		for (attr, defval) in zip(attrs, defvals):
			if attr == "" or attr is None:
				vals[0] = False
				vals = vals + [""]
			else:
				vals = vals + [d.get(attr, defval)]
		return vals

	def list_profiles(self):
		profiles = set()
		for dir_name in self._load_directories:
			try:
				for profile_name in os.listdir(dir_name):
					config_file = self._get_config_filename(dir_name, profile_name)
					if os.path.isfile(config_file):
						profiles.add(profile_name)
			except OSError:
				pass
		return profiles

	def get_known_names(self):
		return sorted(self.list_profiles())

	def get_known_names_summary(self):
		return [(profile, self.get_profile_attrs(profile, [consts.PROFILE_ATTR_SUMMARY], [""])[2]) for profile in sorted(self.list_profiles())]
