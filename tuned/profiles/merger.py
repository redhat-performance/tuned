import collections
from functools import reduce

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
		merged_config = reduce(self._merge_two, configs)
		return merged_config

	def _merge_two(self, profile_a, profile_b):
		"""
		Merge two profiles. The configuration of units with matching names are updated with options
		from the newer profile. If the 'replace' options of the newer unit is 'True', all options from the
		older unit are dropped.
		"""

		profile_a.options.update(profile_b.options)

		for unit_name, unit in list(profile_b.units.items()):
			if unit.replace or unit_name not in profile_a.units:
				profile_a.units[unit_name] = unit
			else:
				profile_a.units[unit_name].type = unit.type
				profile_a.units[unit_name].enabled = unit.enabled
				profile_a.units[unit_name].devices = unit.devices
				if unit.devices_udev_regex is not None:
					profile_a.units[unit_name].devices_udev_regex = unit.devices_udev_regex
				if unit.script_pre is not None:
					profile_a.units[unit_name].script_pre = unit.script_pre
				if unit.script_post is not None:
					profile_a.units[unit_name].script_post = unit.script_post
				if unit_name == "script" and profile_a.units[unit_name].options.get("script", None) is not None:
					script = profile_a.units[unit_name].options.get("script", None)
					profile_a.units[unit_name].options.update(unit.options)
					profile_a.units[unit_name].options["script"] = script + profile_a.units[unit_name].options["script"]
				else:
					profile_a.units[unit_name].options.update(unit.options)

		return profile_a
