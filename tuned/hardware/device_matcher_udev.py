from . import device_matcher
import re

__all__ = ["DeviceMatcherUdev"]

class DeviceMatcherUdev(device_matcher.DeviceMatcher):
	def match(self, regex, device):
		"""
		Match a device against the udev regex in tuning profiles.

		device is a pyudev.Device object
		"""

		properties = ''

		try:
			items = device.properties.items()
		except AttributeError:
			try:
				items = device.items()
			except AttributeError:
				return False

		for key, val in sorted(list(items)):
			properties += key + '=' + val + '\n'

		return re.search(regex, properties, re.MULTILINE) is not None
