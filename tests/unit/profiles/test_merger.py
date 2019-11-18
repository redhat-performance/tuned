import unittest2
from tuned.profiles.merger import Merger
from tuned.profiles.profile import Profile
from collections import OrderedDict

class MergerTestCase(unittest2.TestCase):
	def test_merge_without_replace(self):
		merger = Merger()
		config1 = OrderedDict([
			("main", {"test_option" : "test_value1"}),
			("net", { "devices": "em0", "custom": "custom_value"}),
		])
		profile1 = Profile('test_profile1',config1)
		config2 = OrderedDict([
			('main', {'test_option' : 'test_value2'}),
			('net', { 'devices': 'em1' }),
		])
		profile2 = Profile("test_profile2",config2)

		merged_profile = merger.merge([profile1, profile2])

		self.assertEqual(merged_profile.options["test_option"],"test_value2")
		self.assertIn("net", merged_profile.units)
		self.assertEqual(merged_profile.units["net"].options["custom"],\
			"custom_value")
		self.assertEqual(merged_profile.units["net"].devices, "em1")

	def test_merge_with_replace(self):
		merger = Merger()
		config1 = OrderedDict([
			("main", {"test_option" : "test_value1"}),
			("net", { "devices": "em0", "custom": "option"}),
		])
		profile1 = Profile('test_profile1',config1)
		config2 = OrderedDict([
			("main", {"test_option" : "test_value2"}),
			("net", { "devices": "em1", "replace": True }),
		])
		profile2 = Profile('test_profile2',config2)
		merged_profile = merger.merge([profile1, profile2])

		self.assertEqual(merged_profile.options["test_option"],"test_value2")
		self.assertIn("net", merged_profile.units)
		self.assertNotIn("custom", merged_profile.units["net"].options)
		self.assertEqual(merged_profile.units["net"].devices, "em1")

	def test_merge_multiple_order(self):
		merger = Merger()
		config1 = OrderedDict([ ("main", {"test_option" : "test_value1"}),\
			("net", { "devices": "em0" }) ])
		profile1 = Profile('test_profile1',config1)
		config2 = OrderedDict([	("main", {"test_option" : "test_value2"}),\
			("net", { "devices": "em1" }) ])
		profile2 = Profile('test_profile2',config2)
		config3 = OrderedDict([	("main", {"test_option" : "test_value3"}),\
			("net", { "devices": "em2" }) ])
		profile3 = Profile('test_profile3',config3)
		merged_profile = merger.merge([profile1, profile2, profile3])

		self.assertEqual(merged_profile.options["test_option"],"test_value3")
		self.assertIn("net", merged_profile.units)
		self.assertEqual(merged_profile.units["net"].devices, "em2")
