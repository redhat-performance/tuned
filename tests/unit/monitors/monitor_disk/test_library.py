import unittest

from tests.unit.lib import MockFileOperations
from tuned.monitors.monitor_disk.library import DiskMonitorLibrary
from tuned.utils.file import FileHandler

class DiskMonitorLibraryTestCase(unittest.TestCase):
	def test_is_device_supported(self):
		file_ops = MockFileOperations()
		file_ops.files["/sys/block/sda/device/vendor"] = "ATA"
		file_ops.files["/sys/block/sdb/device/vendor"] = "SCSI"
		file_ops.files["/sys/block/sdc/device/vendor"] = "foo"
		file_handler = FileHandler(file_ops=file_ops)
		lib = DiskMonitorLibrary(file_handler=file_handler)

		self.assertTrue(lib.is_device_supported("sda"))
		self.assertTrue(lib.is_device_supported("sdb"))
		self.assertFalse(lib.is_device_supported("sdc"))

	def test_is_device_supported_nonexistent(self):
		file_ops = MockFileOperations()
		file_handler = FileHandler(file_ops=file_ops)
		lib = DiskMonitorLibrary(file_handler=file_handler)

		self.assertFalse(lib.is_device_supported("sda"))

	def test_get_disk_stats(self):
		file_ops = MockFileOperations()
		file_ops.files["/sys/block/sda/stat"] = "  190950    54349  9473802    36375   110658	 55612	4734707	  626975	0    56856   602279	   0	    0	     0	      0	    5306     9002\n"
		file_handler = FileHandler(file_ops=file_ops)
		lib = DiskMonitorLibrary(file_handler=file_handler)

		res = lib.get_disk_stats("sda")

		expected = [190950, 54349, 9473802, 36375, 110658, 55612,
			    4734707, 626975, 0, 56856, 602279, 0, 0, 0, 0,
			    5306, 9002]
		self.assertEqual(res, expected)
