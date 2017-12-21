import fnmatch
import re

__all__ = ["DeviceMatcher"]

class DeviceMatcher(object):
	"""
	Device name matching against the devices specification in tuning profiles.

	The devices specification consists of multiple rules separated by spaces.
	The rules have a syntax of shell-style wildcards and are either positive
	or negative. The negative rules are prefixed with an exclamation mark.
	"""
	def match(self, rules, device_name):
		"""
		Match a device against the specification in the profile.

		If there is no positive rule in the specification, implicit rule
		which matches all devices is added. The device matches if and only
		if it matches some positive rule, but no negative rule.
		"""
		if isinstance(rules, str):
			rules = re.split(r"\s|,\s*", rules)

		positive_rules = [rule for rule in rules if not rule.startswith("!") and not rule.strip() == '']
		negative_rules = [rule[1:] for rule in rules if rule not in positive_rules]

		if len(positive_rules) == 0:
			positive_rules.append("*")

		matches = False
		for rule in positive_rules:
			if fnmatch.fnmatch(device_name, rule):
				matches = True
				break

		for rule in negative_rules:
			if fnmatch.fnmatch(device_name, rule):
				matches = False
				break

		return matches

	def match_list(self, rules, device_list):
		"""
		Match a device list against the specification in the profile. Returns
		the list, which is a subset of devices which match.
		"""
		matching_devices = []
		for device in device_list:
			if self.match(rules, device):
				matching_devices.append(device)

		return matching_devices
