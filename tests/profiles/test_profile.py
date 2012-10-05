import unittest
import tuned.profiles

class ProfileTestCase(unittest.TestCase):

	def test_init(self):
		tuned.profiles.Profile("test", {})

	def test_init_missing_params(self):
		with self.assertRaises(TypeError):
			tuned.profiles.Profile()

		with self.assertRaises(TypeError):
			tuned.profiles.Profile("test")

	def test_init_extra_params(self):
		with self.assertRaises(TypeError):
			tuned.profiles.Profile("test", {}, "extra")

	def test_create_units(self):
		profile = tuned.profiles.Profile("test", {
			"main": { "anything": 10 },
			"network" : { "type": "net", "devices": "*" },
			"storage" : { "type": "disk" },
		})

		self.assertIs(type(profile.units), list)
		self.assertEqual(len(profile.units), 2)

		for name in ["network", "storage"]:
			for unit in profile.units:
				if unit.name == name:
					break
			else:
				self.assertTrue(False)

	def test_create_units_empty(self):
		profile = tuned.profiles.Profile("test", {"main":{}})

		self.assertIs(type(profile.units), list)
		self.assertEqual(len(profile.units), 0)

	def test_sets_name(self):
		profile1 = tuned.profiles.Profile("test_one", {})
		profile2 = tuned.profiles.Profile("test_two", {})
		self.assertEqual(profile1.name, "test_one")
		self.assertEqual(profile2.name, "test_two")

	def test_sets_options(self):
		profile = tuned.profiles.Profile("test", {
			"main": { "anything": 10 },
			"network" : { "type": "net", "devices": "*" },
		})

		self.assertIs(type(profile.options), dict)
		self.assertEquals(profile.options["anything"], 10)

	def test_sets_options_empty(self):
		profile = tuned.profiles.Profile("test", {
			"storage" : { "type": "disk" },
		})

		self.assertIs(type(profile.options), dict)
		self.assertEquals(len(profile.options), 0)
