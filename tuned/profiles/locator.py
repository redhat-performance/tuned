import os
import tuned.consts as consts
from tuned.utils.config_parser import ConfigParser, Error

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
		ret = None
		conditional_load = profile_name[0:1] == "-"
		if conditional_load:
			profile_name = profile_name[1:]

		for dir_name in reversed(self._load_directories):
			# basename is protection not to get out of the path
			config_file = self._get_config_filename(dir_name, os.path.basename(profile_name))

			if skip_files is not None and config_file in skip_files:
				ret = ""
				continue

			if os.path.isfile(config_file):
				return config_file

		if conditional_load and ret is None:
			ret = ""

		return ret

	def check_profile_name_format(self, profile_name):
		return profile_name is not None and profile_name != "" and "/" not in profile_name

	def parse_config(self, profile_name):
		if not self.check_profile_name_format(profile_name):
			return None
		config_file = self.get_config(profile_name)
		if config_file is None:
			return None
		try:
			config = ConfigParser(delimiters=('='), inline_comment_prefixes=('#'), allow_no_value=True, strict=False)
			config.optionxform = str
			with open(config_file) as f:
				config.read_string("[" + consts.MAGIC_HEADER_NAME + "]\n" + f.read())
			return config
		except (IOError, OSError, Error) as e:
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
		main_unit_in_config = consts.PLUGIN_MAIN_UNIT_NAME in config.sections()
		vals = [True, profile_name]
		for (attr, defval) in zip(attrs, defvals):
			if attr == "" or attr is None:
				vals[0] = False
				vals = vals + [""]
			elif main_unit_in_config and attr in config.options(consts.PLUGIN_MAIN_UNIT_NAME):
				vals = vals + [config.get(consts.PLUGIN_MAIN_UNIT_NAME, attr, raw=True)]
			else:
				vals = vals + [defval]
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
