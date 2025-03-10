import unittest
import tuned.profiles
import collections

class MockProfile(tuned.profiles.profile.Profile):
	def _create_unit(self, name, config):
		return (name, config)

class ProfileTestCase(unittest.TestCase):

	def test_init(self):
		MockProfile("test", {}, None)

	def test_create_units(self):
		profile = MockProfile("test", {
			"main": { "anything": 10 },
			"network" : { "type": "net", "devices": "*" },
			"storage" : { "type": "disk" },
		}, None)

		self.assertIs(type(profile.units), collections.OrderedDict)
		self.assertEqual(len(profile.units), 2)
		self.assertListEqual(sorted([name_config for name_config in profile.units]), sorted(["network", "storage"]))

	def test_create_units_empty(self):
		profile = MockProfile("test", {"main":{}}, None)

		self.assertIs(type(profile.units), collections.OrderedDict)
		self.assertEqual(len(profile.units), 0)

	def test_sets_name(self):
		profile1 = MockProfile("test_one", {}, None)
		profile2 = MockProfile("test_two", {}, None)
		self.assertEqual(profile1.name, "test_one")
		self.assertEqual(profile2.name, "test_two")

	def test_change_name(self):
		profile = MockProfile("oldname", {}, None)
		self.assertEqual(profile.name, "oldname")
		profile.name = "newname"
		self.assertEqual(profile.name, "newname")

	def test_sets_options(self):
		profile = MockProfile("test", {
			"main": { "anything": 10 },
			"network" : { "type": "net", "devices": "*" },
		}, None)

		self.assertIs(type(profile.options), dict)
		self.assertEqual(profile.options["anything"], 10)

	def test_sets_options_empty(self):
		profile = MockProfile("test", {
			"storage" : { "type": "disk" },
		}, None)

		self.assertIs(type(profile.options), dict)
		self.assertEqual(len(profile.options), 0)
