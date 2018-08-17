import unittest2
import pyudev

from tuned.hardware.device_matcher_udev import DeviceMatcherUdev

class DeviceMatcherUdevTestCase(unittest2.TestCase):
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
