import tuned.profiles.unit
import tuned.profiles.variables
import tuned.consts as consts
import collections
import hashlib
import json

class Profile(object):
	"""
	Representation of a tuning profile.
	"""

	__slots__ = ["_name", "_options", "_units", "_variables", "_base_hash"]

	def __init__(self, name, config, variables):
		self._name = name
		self._init_options(config)
		self._init_units(config)
		self._variables = variables
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

	def process_variables(self):
		if "variables" in self.units:
			self._variables.add_from_cfg(self.units["variables"].options)
			del(self.units["variables"])
		# FIXME hack, do all variable expansions in one place
		for unit in self.units:
			self.units[unit].devices = self._variables.expand(self.units[unit].devices)
			self.units[unit].cpuinfo_regex = self._variables.expand(self.units[unit].cpuinfo_regex)
			self.units[unit].uname_regex = self._variables.expand(self.units[unit].uname_regex)

	def as_ordered_dict(self):
		"""generate serializable (with json.dumps()) representation for hashing"""
		profile_dict = collections.OrderedDict()
		profile_dict["main"] = self.options
		profile_dict["variables"] = self._variables.as_ordered_dict()
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
		snapshot += "\n" + self._variables.snapshot()
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
