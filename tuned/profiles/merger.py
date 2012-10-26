import collections

class Merger(object):
	"""
	Tool for merging multiple profiles into one.
	"""

	def __init__(self):
		pass

	def merge(self, configs):
		"""
		Merge multiple configurations into one. If there are multiple units of the same type, option 'devices'
		is set for each unit with respect to eliminating any duplicate devices.
		"""
		for config in configs:
			if not isinstance(config, collections.OrderedDict):
				raise TypeError()

		merged_config = reduce(self._merge_two, configs)
		return merged_config

	def _merge_two(self, config_a, config_b):
		"""
		Merge two configurations. The configuration of units with matching names are updated with options
		from the newer config. If the 'replace' options of the newer unit is 'True', all options from the
		older unit are dropped.
		"""
		new_config = config_a.copy()
		for unit_name, unit_config in config_b.items():
			if unit_config.get("replace", False) or not unit_name in new_config:
				new_config[unit_name] = unit_config.copy()
			else:
				new_config[unit_name].update(unit_config)

		return new_config
