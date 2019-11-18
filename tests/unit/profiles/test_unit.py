import unittest2
from tuned.profiles import Unit

class UnitTestCase(unittest2.TestCase):

	def test_default_options(self):
		unit = Unit("sample", {})
		self.assertEqual(unit.name, "sample")
		self.assertEqual(unit.type, "sample")
		self.assertTrue(unit.enabled)
		self.assertFalse(unit.replace)
		self.assertDictEqual(unit.options, {})

	def test_option_type(self):
		unit = Unit("sample", {"type": "net"})
		self.assertEqual(unit.type, "net")

	def test_option_enabled(self):
		unit = Unit("sample", {"enabled": False})
		self.assertFalse(unit.enabled)
		unit.enabled = True
		self.assertTrue(unit.enabled)

	def test_option_replace(self):
		unit = Unit("sample", {"replace": True})
		self.assertTrue(unit.replace)

	def test_option_custom(self):
		unit = Unit("sample", {"enabled": True, "type": "net", "custom": "value", "foo": "bar"})
		self.assertDictEqual(unit.options, {"custom": "value", "foo": "bar"})
		unit.options = {"hello": "world"}
		self.assertDictEqual(unit.options, {"hello": "world"})

	def test_parsing_options(self):
		unit = Unit("sample", {"type": "net", "enabled": True, "replace": True, "other": "foo"})
		self.assertEqual(unit.type, "net")
