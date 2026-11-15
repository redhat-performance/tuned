import unittest
import pyudev

from tuned.hardware.device_matcher_udev import DeviceMatcherUdev

class DeviceMatcherUdevTestCase(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.udev_context = pyudev.Context()
		cls.matcher = DeviceMatcherUdev()

	def test_simple_search(self):
		try:
			device = pyudev.Devices.from_sys_path(self.udev_context,
				"/sys/devices/virtual/tty/tty0")
		except AttributeError:
			device = pyudev.Device.from_sys_path(self.udev_context,
				"/sys/devices/virtual/tty/tty0")
		self.assertTrue(self.matcher.match("tty0", device))
		try:
			device = pyudev.Devices.from_sys_path(self.udev_context,
				"/sys/devices/virtual/tty/tty1")
		except AttributeError:
			device = pyudev.Device.from_sys_path(self.udev_context,
				"/sys/devices/virtual/tty/tty1")
		self.assertFalse(self.matcher.match("tty0", device))

	def test_regex_search(self):
		try:
			device = pyudev.Devices.from_sys_path(self.udev_context,
				"/sys/devices/virtual/tty/tty0")
		except AttributeError:
			device = pyudev.Device.from_sys_path(self.udev_context,
				"/sys/devices/virtual/tty/tty0")
		self.assertTrue(self.matcher.match("tty.", device))
		self.assertFalse(self.matcher.match("tty[1-9]", device))

	def test_sys_name_matches_through_m_line(self):
		# The sys_name is exposed as the "M=" line even when it does not
		# appear in any of the device's properties. Matching on it must
		# therefore go through that line; removing it breaks this test.
		class FakeProperties(dict):
			pass
		class FakeDevice:
			def __init__(self):
				self.sys_name = "sda3"
				self.properties = FakeProperties({"ID_MODEL": "foo"})
			def items(self):
				return self.properties.items()
		device = FakeDevice()
		# sanity: the sys_name is not present in the properties
		self.assertNotIn("sda3", "".join(
			"%s=%s" % (k, v) for k, v in device.properties.items()))
		self.assertTrue(self.matcher.match("^M=sda3$", device))
		self.assertTrue(self.matcher.match("sda3", device))
		self.assertFalse(self.matcher.match("^M=sda4$", device))

	def test_invalid_regex_does_not_traceback(self):
		# An invalid devices_udev_regex must not raise re.error and break
		# profile application; it should be reported and treated as no match.
		class FakeProperties(dict):
			pass
		class FakeDevice:
			def __init__(self):
				self.sys_name = "fakedev"
				self.properties = FakeProperties({"ID_MODEL": "foo"})
			def items(self):
				return self.properties.items()
		device = FakeDevice()
		self.assertFalse(self.matcher.match("[", device))
		self.assertFalse(self.matcher.match("(a", device))
		self.assertFalse(self.matcher.match("*", device))
