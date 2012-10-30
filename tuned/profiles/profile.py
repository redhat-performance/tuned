import tuned.profiles.unit
import collections

class Profile(object):
	"""
	Representation of a tuning profile.
	"""

	__slots__ = ["_name", "_options", "_units"]

	def __init__(self, name, config):
		self._name = name
		self._init_options(config)
		self._init_units(config)

	def _init_options(self, config):
		self._options = {}
		if "main" in config:
			self._options = dict(config["main"])

	def _init_units(self, config):
		self._units = collections.OrderedDict()
		for unit_name in config:
			if unit_name != "main":
				new_unit = self._create_unit(unit_name, config[unit_name])
				self._units[unit_name] = new_unit

	def _create_unit(self, name, config):
		return tuned.profiles.unit.Unit(name, config)

	@property
	def name(self):
		"""
		Profile name.
		"""
		return self._name

	@name.setter
	def name(self, value):
		self._name = value

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
