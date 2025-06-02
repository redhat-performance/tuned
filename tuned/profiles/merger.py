import tuned.consts as consts
from functools import reduce
from tuned.profiles.profile import Profile

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
		merged_config = reduce(self._merge_two, configs, Profile())
		return merged_config

	def _merge_two(self, profile_a, profile_b):
		"""
		Merge two profiles. The configuration of units with matching names are updated with options
		from the newer profile. If the 'replace' options of the newer unit is 'True', all options from the
		older unit are dropped.
		"""
		if profile_a.name is None:
			profile_a.name = profile_b.name

		profile_a.options.update(profile_b.options)

		for unit_name, unit in list(profile_b.units.items()):
			if unit.type == consts.PLUGIN_VARIABLES_UNIT_NAME:
				if unit.replace:
					profile_a.variables.clear()
				overwritten_variables = set(profile_a.variables.keys()) & set(unit.options.keys())
				profile_a.variables.update(unit.options)
				if unit.prepend:
					for variable in reversed(unit.options):
						if variable not in overwritten_variables:
							profile_a.variables.move_to_end(variable, last=False)
			elif unit.replace or unit_name not in profile_a.units:
				profile_a.units[unit_name] = unit
			else:
				profile_a.units[unit_name].type = unit.type
				profile_a.units[unit_name].enabled = unit.enabled
				profile_a.units[unit_name].devices = unit.devices
				if unit.priority is not None:
					profile_a.units[unit_name].priority = unit.priority
				if unit.devices_udev_regex is not None:
					profile_a.units[unit_name].devices_udev_regex = unit.devices_udev_regex
				if unit.cpuinfo_regex is not None:
					profile_a.units[unit_name].cpuinfo_regex = unit.cpuinfo_regex
				if unit.uname_regex is not None:
					profile_a.units[unit_name].uname_regex = unit.uname_regex
				if unit.script_pre is not None:
					profile_a.units[unit_name].script_pre = unit.script_pre
				if unit.script_post is not None:
					profile_a.units[unit_name].script_post = unit.script_post
				if unit.drop is not None:
					for option in unit.drop:
						profile_a.units[unit_name].options.pop(option, None)
					unit.drop = None
				if unit_name == "script" and profile_a.units[unit_name].options.get("script", None) is not None:
					script = profile_a.units[unit_name].options.get("script", None)
					profile_a.units[unit_name].options.update(unit.options)
					profile_a.units[unit_name].options["script"] = script + profile_a.units[unit_name].options["script"]
				else:
					profile_a.units[unit_name].options.update(unit.options)

		return profile_a
