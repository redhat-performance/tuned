import unittest2
import pyudev

from tuned.hardware.device_matcher_udev import DeviceMatcherUdev

class DeviceMatcherUdevTestCase(unittest2.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.udev_context = pyudev.Context()
		cls.matcher = DeviceMatcherUdev()


	def test_simple_search(self):
		device = pyudev.Devices.from_path(self.udev_context,'/devices/virtual/cpuid/cpu0')
		self.assertTrue(self.matcher.match('cpu0',device))
		device = pyudev.Devices.from_path(self.udev_context,'/devices/virtual/cpuid/cpu1')
		self.assertFalse(self.matcher.match('cpu0',device))


	def test_regex_search(self):
		device = pyudev.Devices.from_path(self.udev_context,'/devices/virtual/cpuid/cpu0')
		self.assertTrue(self.matcher.match('cpu.',device))
		device = pyudev.Devices.from_path(self.udev_context,'/devices/virtual/cpuid/cpu0')
		self.assertFalse(self.matcher.match('cpu[1-9]',device))
