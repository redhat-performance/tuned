import unittest
from unittest.mock import patch

from tuned.profiles.functions.function_cpuinfo_check import CPUInfoCheck


class CPUInfoCheckTestCase(unittest.TestCase):
	def test_invalid_regex_uses_fallback(self):
		function = CPUInfoCheck()
		with patch.object(function._cmd, "read_file", return_value="cpu data"):
			self.assertEqual("fallback", function.execute(["[", "matched", "fallback"]))
