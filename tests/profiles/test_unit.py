import unittest
import tuned.profiles

class UnitTestCase(unittest.TestCase):

	def test_init(self):
		unit = tuned.profiles.Unit("network", "net", {})

	def test_init_missing_params(self):
		with self.assertRaises(TypeError):
			tuned.profiles.Unit()

	def test_init_extra_params(self):
		with self.assertRaises(TypeError):
			tuned.profiles.Unit("a", "b", {}, "c")

	def test_attributes(self):
		unit = tuned.profiles.Unit("network", "net", {"devices": "em1"})
		self.assertEqual(unit.name, "network")
		self.assertEqual(unit.plugin, "net")
		self.assertEqual(unit.options["devices"], "em1")

		unit2 = tuned.profiles.Unit("test", "disk", {"enabled": True})
		self.assertEqual(unit2.name, "test")
		self.assertEqual(unit2.plugin, "disk")
		self.assertTrue(unit2.options["enabled"])
