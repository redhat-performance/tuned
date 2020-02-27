import errno
import unittest

from tests.unit.lib import create_IOError, MockFileOperations
import tuned.consts as consts
from tuned.exceptions import TunedException
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

	def test_get_active_profile_inaccessible(self):
		class MyFileOps(MockFileOperations):
			def read(self, path):
				self.read_called += 1
				if path == consts.ACTIVE_PROFILE_FILE:
					raise create_IOError(errno.EACCES, path)
				elif path == consts.PROFILE_MODE_FILE:
					return 'auto'
				else:
					raise create_IOError(errno.ENOENT, path)
		file_ops = MyFileOps()
		file_handler = FileHandler(file_ops=file_ops)
		active_profile_manager = ActiveProfileManager(
				file_handler=file_handler)

		self.assertRaises(TunedException, active_profile_manager.get)
		self.assertEqual(file_ops.write_called, 0)

	def test_get_profile_mode_inaccessible(self):
		class MyFileOps(MockFileOperations):
			def read(self, path):
				self.read_called += 1
				if path == consts.ACTIVE_PROFILE_FILE:
					return 'test_profile'
				elif path == consts.PROFILE_MODE_FILE:
					raise create_IOError(errno.EACCES, path)
				else:
					raise create_IOError(errno.ENOENT, path)
		file_ops = MyFileOps()
		file_handler = FileHandler(file_ops=file_ops)
		active_profile_manager = ActiveProfileManager(
				file_handler=file_handler)

		self.assertRaises(TunedException, active_profile_manager.get)
		self.assertEqual(file_ops.write_called, 0)

	def test_get_invalid_profile_mode(self):
		file_ops = MockFileOperations()
		file_ops.files[consts.ACTIVE_PROFILE_FILE] = 'test_profile'
		file_ops.files[consts.PROFILE_MODE_FILE] = 'foo'
		file_handler = FileHandler(file_ops=file_ops)
		active_profile_manager = ActiveProfileManager(
				file_handler=file_handler)

		self.assertRaises(TunedException, active_profile_manager.get)
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

	def test_save_profile_name_None(self):
		file_ops = MockFileOperations()
		file_handler = FileHandler(file_ops=file_ops)
		active_profile_manager = ActiveProfileManager(
				file_handler=file_handler)

		active_profile_manager.save(None, False)

		active_profile = file_ops.files[consts.ACTIVE_PROFILE_FILE]
		self.assertEqual(active_profile, '')
		profile_mode = file_ops.files[consts.PROFILE_MODE_FILE]
		self.assertEqual(profile_mode, 'auto\n')
		self.assertEqual(file_ops.read_called, 0)

	def test_save_active_profile_inaccessible(self):
		class MyFileOps(MockFileOperations):
			def write(self, path, contents):
				self.write_called += 1
				if path == consts.ACTIVE_PROFILE_FILE:
					raise create_IOError(errno.EACCES, path)
				else:
					self.files[path] = contents

		file_ops = MyFileOps()
		file_handler = FileHandler(file_ops=file_ops)
		active_profile_manager = ActiveProfileManager(
				file_handler=file_handler)

		self.assertRaises(TunedException,
				  active_profile_manager.save,
				  'test_profile', False)

		self.assertEqual(file_ops.read_called, 0)

		# The profile mode file may or may not have been saved. Check
		# that no other files were written.
		self.assertIn(file_ops.write_called, [1, 2])
		self.assertEqual(len(file_ops.files), file_ops.write_called - 1)
		if file_ops.files:
			self.assertEqual(file_ops.files[consts.PROFILE_MODE_FILE],
					 'auto\n')

	def test_save_profile_mode_inaccessible(self):
		class MyFileOps(MockFileOperations):
			def write(self, path, contents):
				self.write_called += 1
				if path == consts.PROFILE_MODE_FILE:
					raise create_IOError(errno.EACCES, path)
				else:
					self.files[path] = contents

		file_ops = MyFileOps()
		file_handler = FileHandler(file_ops=file_ops)
		active_profile_manager = ActiveProfileManager(
				file_handler=file_handler)

		self.assertRaises(TunedException,
				  active_profile_manager.save,
				  'test_profile', False)

		self.assertEqual(file_ops.read_called, 0)

		# The active profile file may or may not have been
		# saved. Check that no other files were written.
		self.assertIn(file_ops.write_called, [1, 2])
		self.assertEqual(len(file_ops.files), file_ops.write_called - 1)
		if file_ops.files:
			self.assertEqual(file_ops.files[consts.ACTIVE_PROFILE_FILE],
					 'test_profile\n')
