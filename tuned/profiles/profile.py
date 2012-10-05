import tuned.profiles.unit

class Profile(object):
	"""
	Representation of a tuning profile.
	"""

	__slots__ = ["_config", "_options", "_units"]

	def __init__(self, config):
		self._config = config
		self._init_options(config)
		self._init_units(config)

	def _init_options(self, config):
		self._options = {}
		if "main" in config:
			self._options = config["main"].copy()

	def _init_units(self, config):
		self._units = []
		for unit_name in config:
			if unit_name != "main":
				new_unit = self._create_unit(unit_name, config[unit_name])
				self._units.append(new_unit)

	def _create_unit(self, name, config_options):
		options = config_options.copy()
		plugin = options.pop("type")
		return tuned.profiles.unit.Unit(name, plugin, options)

	@property
	def units(self):
		"""
		Units included in the profile.
		"""
		return self._units

	@property
	def options(self):
		"""
		Profile global options.
		"""
		return self._options
