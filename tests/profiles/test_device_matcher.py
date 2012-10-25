import unittest
from tuned.profiles.device_matcher import DeviceMatcher

class DeviceMatcherTestCase(unittest.TestCase):
	def test_one_positive_rule(self):
		self.assertTrue(DeviceMatcher.match("sd*", "sda"))
		self.assertFalse(DeviceMatcher.match("sd*", "hda"))

	def test_multiple_positive_rules(self):
		self.assertTrue(DeviceMatcher.match("sd* hd*", "sda"))
		self.assertTrue(DeviceMatcher.match("sd* hd*", "hda"))
		self.assertFalse(DeviceMatcher.match("sd* hd*", "dm-0"))

	def test_implicit_positive(self):
		self.assertTrue(DeviceMatcher.match("", "sda"))
		self.assertTrue(DeviceMatcher.match("!sd*", "hda"))
		self.assertFalse(DeviceMatcher.match("!sd*", "sda"))

	def test_positve_negative_combination(self):
		self.assertTrue(DeviceMatcher.match("sd* !sdb", "sda"))
		self.assertFalse(DeviceMatcher.match("sd* !sdb", "sdb"))

	def test_positive_first(self):
		self.assertTrue(DeviceMatcher.match("!sdb sd*", "sda"))
		self.assertFalse(DeviceMatcher.match("!sdb sd*", "sdb"))
