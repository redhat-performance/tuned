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

		# The udev INTERFACE property is written to the udev database only
		# after udev finishes processing an interface rename, so it can lag
		# behind the live kernel name (e.g. report "eth0" while the interface
		# is already "ens8f0np0"). Match the interface name against sys_name
		# instead, which is the authoritative current name and updates in sync
		# with the rename.
		for key, val in sorted(list(items)):
			if key == "INTERFACE":
				val = device.sys_name
			properties += key + '=' + val + '\n'

		try:
			return re.search(regex, properties, re.MULTILINE) is not None
		except re.error:
			log.error("Invalid regular expression in devices_udev_regex: '%s'" % regex)
			return False
