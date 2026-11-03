from . import device_matcher
import re
import tuned.logs

__all__ = ["DeviceMatcherUdev"]

log = tuned.logs.get()

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

		# Expose the sysfs name as "M" for every device, mirroring the udev CLI
		# tools (`udevadm info` reports it on the "M:" line).
		try:
			properties += 'M=' + device.sys_name + '\n'
		except AttributeError:
			pass

		try:
			return re.search(regex, properties, re.MULTILINE) is not None
		except re.error:
			log.error("Invalid regular expression in devices_udev_regex: '%s'" % regex)
			return False
