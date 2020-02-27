import unittest

from tests.unit.lib import MockFileOperations
from tuned.profiles.functions.function_cpuinfo_check.library import CPUInfoLibrary
from tuned.utils.file import FileHandler

class CPUInfoTestCase(unittest.TestCase):
	def test_cpuinfo_match(self):
		file_ops = MockFileOperations()
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPUInfoLibrary(file_handler)

		file_ops.files["/proc/cpuinfo"] = "processor\t: 0\nvendor_id\t: GenuineIntel\n"
		res = lib.cpuinfo_match(["GenuineIntel", "foo"])
		self.assertEqual(res, "foo")

		file_ops.files["/proc/cpuinfo"] = "processor\t: 0\nvendor_id\t: GenuineIntel\n"
		res = lib.cpuinfo_match(["GenuineIntel", "foo", "bar"])
		self.assertEqual(res, "foo")

		file_ops.files["/proc/cpuinfo"] = "processor\t: 0\nvendor_id\t: GenuineIntel\n"
		res = lib.cpuinfo_match(["GenuineIntel", "foo", "AMD", "bar"])
		self.assertEqual(res, "foo")

		file_ops.files["/proc/cpuinfo"] = "processor\t: 0\nvendor_id\t: GenuineIntel\n"
		res = lib.cpuinfo_match(["AMD", "foo"])
		self.assertEqual(res, "")

		file_ops.files["/proc/cpuinfo"] = "processor\t: 0\nvendor_id\t: GenuineIntel\n"
		res = lib.cpuinfo_match(["AMD", "foo", "bar"])
		self.assertEqual(res, "bar")

		file_ops.files["/proc/cpuinfo"] = "processor\t: 0\nvendor_id\t: GenuineIntel\n"
		res = lib.cpuinfo_match(["AMD", "foo", "GenuineIntel", "bar"])
		self.assertEqual(res, "bar")

		file_ops.files["/proc/cpuinfo"] = "processor\t: 0\nvendor_id\t: GenuineIntel\n"
		res = lib.cpuinfo_match([".*", "foo"])
		self.assertEqual(res, "foo")

		file_ops.files["/proc/cpuinfo"] = "processor\t: 0\nvendor_id\t: GenuineIntel\n"
		res = lib.cpuinfo_match(["AMD", "foo", ".*", "bar"])
		self.assertEqual(res, "bar")


		file_ops.files["/proc/cpuinfo"] = "processor\t: 0\nvendor_id\t: GenuineIntel\n"
		res = lib.cpuinfo_match(["AMD", "foo", "IBM", "bar"])
		self.assertEqual(res, "")

	def test_cpuinfo_match_nonexistent(self):
		file_ops = MockFileOperations()
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPUInfoLibrary(file_handler)

		res = lib.cpuinfo_match(["GenuineIntel", "foo"])

		self.assertEqual(res, "")
