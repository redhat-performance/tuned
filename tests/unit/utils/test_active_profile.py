import unittest

from tests.unit.lib import MockFileOperations
import tuned.consts as consts
from tuned.utils.active_profile import ActiveProfileManager
from tuned.utils.file import FileHandler

class ActiveProfileManagerTestCase(unittest.TestCase):
	def test_get(self):
		file_ops = MockFileOperations()
		file_ops.files[consts.ACTIVE_PROFILE_FILE] = 'test_profile'
		file_ops.files[consts.PROFILE_MODE_FILE] = 'auto'
		file_handler = FileHandler(file_ops=file_ops)
		active_profile_manager = ActiveProfileManager(
				file_handler=file_handler)

		(profile, mode) = active_profile_manager.get()

		self.assertEqual(profile, 'test_profile')
		self.assertEqual(mode, False)

		del file_ops.files[consts.ACTIVE_PROFILE_FILE]
		del file_ops.files[consts.PROFILE_MODE_FILE]
		(profile, mode) = active_profile_manager.get()

		self.assertEqual(profile, None)
		self.assertEqual(mode, None)
		self.assertEqual(file_ops.write_called, 0)

	def test_save(self):
		file_ops = MockFileOperations()
		file_handler = FileHandler(file_ops=file_ops)
		active_profile_manager = ActiveProfileManager(
				file_handler=file_handler)

		active_profile_manager.save('test_profile', False)

		active_profile = file_ops.files[consts.ACTIVE_PROFILE_FILE]
		self.assertEqual(active_profile, 'test_profile\n')
		profile_mode = file_ops.files[consts.PROFILE_MODE_FILE]
		self.assertEqual(profile_mode, 'auto\n')
		self.assertEqual(file_ops.read_called, 0)
