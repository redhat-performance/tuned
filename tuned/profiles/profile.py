import tuned.profiles.unit
import tuned.consts as consts
import collections
import hashlib
import json

class Profile(object):
	"""
	Representation of a tuning profile.
	"""

	__slots__ = ["_name", "_options", "_variables", "_units", "_base_hash"]

	def __init__(self, name=None, config={}):
		self._name = name
		self._variables = collections.OrderedDict()
		self._init_options(config)
		self._init_units(config)
		self._base_hash = config.get("main", {}).get("profile_base_hash", None)

	def _init_options(self, config):
		self._options = {}
		if consts.PLUGIN_MAIN_UNIT_NAME in config:
			self._options = collections.OrderedDict(config[consts.PLUGIN_MAIN_UNIT_NAME])

	def _init_units(self, config):
		self._units = collections.OrderedDict()
		for unit_name in config:
			if unit_name != consts.PLUGIN_MAIN_UNIT_NAME:
				new_unit = self._create_unit(unit_name, config[unit_name])
				self._units[unit_name] = new_unit

	def _create_unit(self, name, config):
		return tuned.profiles.unit.Unit(name, config)

	def as_ordered_dict(self):
		"""generate serializable (with json.dumps()) representation for hashing"""
		profile_dict = collections.OrderedDict()
		profile_dict["main"] = self.options
		profile_dict["variables"] = self._variables
		for name, unit in self._units.items():
			profile_dict[name] = unit.as_ordered_dict()
		return profile_dict

	def calculate_hash(self):
		serialized = json.dumps(self.as_ordered_dict())
		self._base_hash = hashlib.md5(serialized.encode(), usedforsecurity=False).hexdigest()

	def snapshot(self, instances):
		"""generate config representation that will re-create the data when read as a profile"""
		snapshot = "[main]\n"
		snapshot += "active_profile=%s\n" % self.name
		snapshot += "profile_base_hash=%s\n" % self._base_hash
		snapshot += "\n[variables]\n"
		for key, value in self._variables.items():
			snapshot += "%s=%s\n" % (key, value)
		for unit in self.units.values():
			snapshot += "\n" + unit.snapshot()
			for instance in instances:
				if instance.name == unit.name:
					snapshot += "__devices__=%s\n" % " ".join(instance.assigned_devices | instance.processed_devices)
					break
		return snapshot

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
	def variables(self):
		return self._variables

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
