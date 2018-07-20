import unittest2
from tuned.hardware.device_matcher import DeviceMatcher

class DeviceMatcherTestCase(unittest2.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.matcher = DeviceMatcher()

	def test_one_positive_rule(self):
		self.assertTrue(self.matcher.match("sd*", "sda"))
		self.assertFalse(self.matcher.match("sd*", "hda"))

	def test_multiple_positive_rules(self):
		self.assertTrue(self.matcher.match("sd* hd*", "sda"))
		self.assertTrue(self.matcher.match("sd* hd*", "hda"))
		self.assertFalse(self.matcher.match("sd* hd*", "dm-0"))

	def test_implicit_positive(self):
		self.assertTrue(self.matcher.match("", "sda"))
		self.assertTrue(self.matcher.match("!sd*", "hda"))
		self.assertFalse(self.matcher.match("!sd*", "sda"))

	def test_positve_negative_combination(self):
		self.assertTrue(self.matcher.match("sd* !sdb", "sda"))
		self.assertFalse(self.matcher.match("sd* !sdb", "sdb"))

	def test_positive_first(self):
		self.assertTrue(self.matcher.match("!sdb sd*", "sda"))
		self.assertFalse(self.matcher.match("!sdb sd*", "sdb"))

	def test_match_list(self):
		devices = ["sda", "sdb", "sdc"]
		self.assertListEqual(self.matcher.match_list("sd* !sdb", devices), ["sda", "sdc"])
		self.assertListEqual(self.matcher.match_list("!sda", devices), ["sdb", "sdc"])
