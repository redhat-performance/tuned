import unittest
from tuned.profiles.merger import Merger
from collections import OrderedDict

class MergerTestCase(unittest.TestCase):
	def test_merge_without_replace(self):
		merger = Merger()
		config1 = OrderedDict([
			("main", OrderedDict()),
			("net", { "devices": "em0", "custom": "option"}),
		])
		config2 = OrderedDict([
			("main", OrderedDict()),
			("net", { "devices": "em1" }),
		])
		config = merger.merge([config1, config2])

		self.assertIn("main", config)
		self.assertIn("net", config)
		self.assertEqual(config["net"]["custom"], "option")
		self.assertEqual(config["net"]["devices"], "em1")

	def test_merge_with_replace(self):
		merger = Merger()
		config1 = OrderedDict([
			("main", OrderedDict()),
			("net", { "devices": "em0", "custom": "option"}),
		])
		config2 = OrderedDict([
			("main", OrderedDict()),
			("net", { "devices": "em1", "replace": True }),
		])
		config = merger.merge([config1, config2])

		self.assertIn("main", config)
		self.assertIn("net", config)
		self.assertNotIn("custom", config["net"])
		self.assertEqual(config["net"]["devices"], "em1")

	def test_merge_multiple_order(self):
		merger = Merger()
		config1 = OrderedDict([ ("main", OrderedDict()), ("net", { "devices": "em0" }) ])
		config2 = OrderedDict([	("main", OrderedDict()), ("net", { "devices": "em1" }) ])
		config3 = OrderedDict([	("main", OrderedDict()), ("net", { "devices": "em2" }) ])
		config = merger.merge([config1, config2, config3])

		self.assertIn("main", config)
		self.assertIn("net", config)
		self.assertEqual(config["net"]["devices"], "em2")
