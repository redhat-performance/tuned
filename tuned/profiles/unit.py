class Unit(object):
	"""
	Unit description.
	"""

	__slots__ = [ "_name", "_type", "_enabled", "_replace", "_options" ]

	def __init__(self, name, config):
		self._name = name
		self._type = config.pop("type", self._name)
		self._enabled = config.pop("enabled", True) in [True, "true", 1]
		self._replace = config.pop("replace", False) in [True, "true", 1]
		self._options = dict(config)

	@property
	def name(self):
		return self._name

	@property
	def type(self):
		return self._type

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
	def options(self):
		return self._options

	@options.setter
	def options(self, value):
		self._options = value
