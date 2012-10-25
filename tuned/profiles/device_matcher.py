import fnmatch

class DeviceMatcher(object):
	"""
	Device name matching against the devices specification in tuning profiles.

	The devices specification consists of multiple rules separated by spaces.
	The rules have a syntax of shell-style wildcards and are either positive
	or negative. The negative rules are prefixed with an exclamation mark.
	"""
	@classmethod
	def match(cls, rules_str, device_name):
		"""
		Match a device against the specification in the profile.

		If there is no positive rule in the specification, implicit rule
		which matches all devices is added. The device matches if and only
		if it matches some positive rule, but no negative rule.
		"""
		rules = rules_str.split()
		positive_rules = filter(lambda rule: not rule.startswith("!"), rules)
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
