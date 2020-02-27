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
