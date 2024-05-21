import collections
from functools import reduce
import tuned.logs
log = tuned.logs.get()

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

	def join(self, configs):
		"""
                Join multiple configurations and append them to a list. This option can be used to apply multiple
		profiles accross different set of cores simultaneously. To know more about this merge_type, please refer
                to this document https://docs.google.com/document/d/1Tb6LygN8aM5pdX7akqNe3Wsn65O3oBkPZBEKEX6tZ_s/edit?usp=sharing.
                """
		joined_config = reduce(self._join_two, configs)
		return joined_config

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

	def _join_two(self, profile_a, profile_b):
		"""
                Join two profiles. The configuration of units with matching names are updated based on the merge_type
                the newer profile. If the merge_type of newer profile is "join", append it to the list of existing units.
		If the merge_type of the newer_profile is "apply", replace(existing Merge merger mechanism).
		If the 'replace' options of the newer unit is 'True', all options from the older unit are dropped.
                """

		if type(list(profile_a.units.values())[0]) != list:
                        profile_a_modified = collections.OrderedDict([(k,[v]) for k,v in profile_a.units.items()])
                        profile_a.units.clear()
                        profile_a.units.update(profile_a_modified)

		for unit_name, unit in list(profile_b.units.items()):
			if unit.replace or unit_name not in profile_a.units:
                                profile_a.units[unit_name] = [unit]

			else:
                                if profile_b.units[unit_name].merge_type == "join":
                                        profile_a.units[unit_name].append(unit)

                                elif profile_b.units[unit_name].merge_type != "join":
                                        if len(profile_a.units[unit_name]) > 1:
                                                log.warn("Cannot replace already joined units.")
                                        else:
                                                profile_a.units[unit_name][0].type = unit.type
                                                profile_a.units[unit_name][0].enabled = unit.enabled
                                                profile_a.units[unit_name][0].devices = unit.devices
                                                if unit.devices_udev_regex is not None:
                                                        profile_a.units[unit_name][0].devices_udev_regex = unit.devices_udev_regex
                                                if unit.cpuinfo_regex is not None:
                                                        profile_a.units[unit_name][0].cpuinfo_regex = unit.cpuinfo_regex
                                                if unit.uname_regex is not None:
                                                        profile_a.units[unit_name][0].uname_regex = unit.uname_regex
                                                if unit.script_pre is not None:
                                                        profile_a.units[unit_name][0].script_pre = unit.script_pre
                                                if unit.script_post is not None:
                                                        profile_a.units[unit_name][0].script_post = unit.script_post
                                                if unit.drop is not None:
                                                        for option in unit.drop:
                                                                profile_a.units[unit_name][0].options.pop(option, None)
                                                        unit.drop = None
                                                if unit_name == "script" and profile_a.units[unit_name][0].options.get("script", None) is not None:
                                                        script = profile_a.units[unit_name][0].options.get("script", None)
                                                        profile_a.units[unit_name][0].options.update(unit.options)
                                                        profile_a.units[unit_name][0].options["script"] = script + profile_a.units[unit_name][0].options["script"]
                                                else:
                                                        profile_a.units[unit_name][0].options.update(unit.options)

		return profile_a
