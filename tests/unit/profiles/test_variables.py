import unittest
import tempfile
import shutil
from tuned.profiles import variables, profile

class VariablesTestCase(unittest.TestCase):

	@classmethod
	def setUpClass(cls):
		cls.test_dir = tempfile.mkdtemp()

		with open(cls.test_dir + "/variables", 'w') as f:
			f.write("variable1=var1\n")

	def test_from_file(self):
		v = variables.Variables()
		v.add_from_file(self.test_dir + "/variables")
		self.assertEqual("This is var1", v.expand("This is ${variable1}"))

	def test_from_unit(self):
		mock_unit = {
			"include": self.test_dir + "/variables",
			"variable2": "var2"
		}
		v = variables.Variables()
		v.add_from_cfg(mock_unit)

		self.assertEqual("This is var1 and this is var2", v.expand("This is ${variable1} and this is ${variable2}"))

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls.test_dir)
