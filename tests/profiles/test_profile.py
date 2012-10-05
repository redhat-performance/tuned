import unittest
import tuned.profiles

class ProfileTestCase(unittest.TestCase):

	def test_init(self):
		tuned.profiles.Profile({})

	def test_init_missing_params(self):
		with self.assertRaises(TypeError):
			tuned.profiles.Profile()

	def test_init_extra_params(self):
		with self.assertRaises(TypeError):
			tuned.profiles.Profile({}, "extra")

	def test_create_units(self):
		profile = tuned.profiles.Profile({
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
		profile = tuned.profiles.Profile({"main":{}})

		self.assertIs(type(profile.units), list)
		self.assertEqual(len(profile.units), 0)

	def test_sets_options(self):
		profile = tuned.profiles.Profile({
			"main": { "anything": 10 },
			"network" : { "type": "net", "devices": "*" },
		})

		self.assertIs(type(profile.options), dict)
		self.assertEquals(profile.options["anything"], 10)

	def test_sets_options_empty(self):
		profile = tuned.profiles.Profile({
			"storage" : { "type": "disk" },
		})

		self.assertIs(type(profile.options), dict)
		self.assertEquals(len(profile.options), 0)
