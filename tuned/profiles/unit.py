import collections

class Unit(object):
	"""
	Unit description.
	"""

	__slots__ = [ "_name", "_type", "_enabled", "_replace", "_devices", "_devices_udev_regex", \
		"_script_pre", "_script_post", "_options" ]

	def __init__(self, name, config):
		self._name = name
		self._type = config.pop("type", self._name)
		self._enabled = config.pop("enabled", True) in [True, "true", 1]
		self._replace = config.pop("replace", False) in [True, "true", 1]
		self._devices = config.pop("devices", "*")
		self._devices_udev_regex = config.pop("devices_udev_regex", None)
		self._script_pre = config.pop("script_pre", None)
		self._script_post = config.pop("script_post", None)
		self._options = collections.OrderedDict(config)

	@property
	def name(self):
		return self._name

	@property
	def type(self):
		return self._type

	@type.setter
	def type(self, value):
		self._type = value

	@property
	def enabled(self):
		return self._enabled

	@enabled.setter
	def enabled(self, value):
		self._enabled = value

	@property
	def replace(self):
		return self._replace

	@property
	def devices(self):
		return self._devices

	@devices.setter
	def devices(self, value):
		self._devices = value

	@property
	def devices_udev_regex(self):
		return self._devices_udev_regex

	@devices_udev_regex.setter
	def devices_udev_regex(self, value):
		self._devices_udev_regex = value

	@property
	def script_pre(self):
		return self._script_pre

	@script_pre.setter
	def script_pre(self, value):
		self._script_pre = value

	@property
	def script_post(self):
		return self._script_post

	@script_post.setter
	def script_post(self, value):
		self._script_post = value

	@property
	def options(self):
		return self._options

	@options.setter
	def options(self, value):
		self._options = value
