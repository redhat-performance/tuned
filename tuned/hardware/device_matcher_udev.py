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
		for key, val in list(device.items()):
			properties += key + '=' + val + '\n'

		return re.search(regex, properties, re.MULTILINE) is not None
