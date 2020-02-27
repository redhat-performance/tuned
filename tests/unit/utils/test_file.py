import errno
import os
import shutil
import tempfile
import unittest

from tests.unit.lib import create_IOError, MockFileOperations, MockLogger
from tuned.utils.file import FileHandler, FileOperations

class FileOperationsTestCase(unittest.TestCase):
	def setUp(self):
		self._test_dir = tempfile.mkdtemp()

	def test_read_raises_errors(self):
		path = os.path.join(self._test_dir, 'foo')
		try:
			FileOperations.read(path)
			self.fail()
		except IOError as e:
			self.assertEqual(e.errno, errno.ENOENT)
		open(path, 'w').close()
		os.chmod(path, 0)
		try:
			FileOperations.read(path)
			self.fail()
		except IOError as e:
			self.assertEqual(e.errno, errno.EACCES)
		os.unlink(path)

	def test_read(self):
		path = os.path.join(self._test_dir, 'foo')
		open(path, 'w').close()
		self.assertEqual(FileOperations.read(path), '')

		contents = 'foo\nbar\n'
		with open(path, 'w') as f:
			f.write(contents)
		self.assertEqual(FileOperations.read(path), contents)
		os.unlink(path)

	def test_write_raises_errors(self):
		path = os.path.join(self._test_dir, 'foo')
		open(path, 'w').close()
		os.chmod(path, 0)
		try:
			FileOperations.write(path, 'foobar')
			self.fail()
		except IOError as e:
			self.assertEqual(e.errno, errno.EACCES)
		os.unlink(path)

	def test_write(self):
		path = os.path.join(self._test_dir, 'foo')
		contents = 'bar\nfoo\n'
		FileOperations.write(path, contents)
		with open(path, 'r') as f:
			self.assertEqual(f.read(), contents)
		os.unlink(path)

	def tearDown(self):
		shutil.rmtree(self._test_dir)

class MockFileOperationsNoOp(object):
	@staticmethod
	def read(path):
		pass

	@staticmethod
	def write(path, contents):
		pass

class FileHandlerTestCase(unittest.TestCase):
	def test_no_errors_with_static_fileops_without_log(self):
		fh = FileHandler(file_ops=MockFileOperationsNoOp)
		fh.read('foo')
		fh.write('foo', 'bar')

	def test_read(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		fh = FileHandler(file_ops=file_ops,
				 log_func=logger.debug)
		test_path = 'foo'
		test_contents = 'foo\nbar\n'
		file_ops.files[test_path] = test_contents

		contents = fh.read(test_path)

		self.assertEqual(contents, test_contents)
		self.assertEqual(file_ops.read_called, 1)
		self.assertEqual(file_ops.write_called, 0)
		self.assertEqual(len(logger.msgs), 2)
		self.assertEqual(logger.msgs[0],
				 ("debug", "Reading file '%s'" % test_path))
		self.assertEqual(logger.msgs[1],
				 ("debug", "Contents of the file '%s':\n%s"
				  % (test_path, test_contents)))

	def test_read_with_error(self):
		logger = MockLogger()
		file_ops = MockFileOperations(error_to_raise=errno.EACCES)
		fh = FileHandler(file_ops=file_ops,
				 log_func=logger.debug)
		test_path = 'foo'

		try:
			fh.read(test_path)
			self.fail()
		except IOError as e:
			self.assertEqual(e.errno, errno.EACCES)

		self.assertEqual(file_ops.read_called, 1)
		self.assertEqual(file_ops.write_called, 0)
		self.assertEqual(len(logger.msgs), 2)
		self.assertEqual(logger.msgs[0],
				 ("debug", "Reading file '%s'" % test_path))
		expected_error = create_IOError(errno.EACCES, test_path)
		self.assertEqual(logger.msgs[1],
				 ("debug", "Failed to read file '%s': %s"
				  % (test_path, expected_error)))

	def test_read_with_error_with_log_error(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		fh = FileHandler(file_ops=file_ops,
				log_func=logger.debug,
				log_error_func=logger.error)
		test_path = 'foo'

		try:
			fh.read(test_path)
			self.fail()
		except IOError as e:
			self.assertEqual(e.errno, errno.ENOENT)

		self.assertEqual(file_ops.read_called, 1)
		self.assertEqual(file_ops.write_called, 0)
		self.assertEqual(len(logger.msgs), 2)
		self.assertEqual(logger.msgs[0],
				 ("debug", "Reading file '%s'" % test_path))
		expected_error = create_IOError(errno.ENOENT, test_path)
		self.assertEqual(logger.msgs[1],
				 ("error", "Failed to read file '%s': %s"
				  % (test_path, expected_error)))

	def test_write(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		fh = FileHandler(file_ops=file_ops,
				 log_func=logger.debug)
		test_path = 'foo'
		test_contents = 'foo\nbar\n'

		fh.write(test_path, test_contents)

		self.assertEqual(file_ops.files[test_path], test_contents)
		self.assertEqual(file_ops.read_called, 0)
		self.assertEqual(file_ops.write_called, 1)
		self.assertEqual(len(logger.msgs), 2)
		self.assertEqual(logger.msgs[0],
				 ("debug", "Writing to file '%s' the following:\n%s"
				  % (test_path, test_contents)))
		self.assertEqual(logger.msgs[1],
				 ("debug", "Finished writing to file '%s" % test_path))

	def test_write_with_error(self):
		logger = MockLogger()
		file_ops = MockFileOperations(error_to_raise=errno.EACCES)
		fh = FileHandler(file_ops=file_ops,
				 log_func=logger.debug)
		test_path = 'foo'
		test_contents = 'foo\nbar\n'

		try:
			fh.write(test_path, test_contents)
			self.fail()
		except IOError as e:
			self.assertEqual(e.errno, errno.EACCES)

		self.assertEqual(file_ops.read_called, 0)
		self.assertEqual(file_ops.write_called, 1)
		self.assertEqual(len(logger.msgs), 2)
		self.assertEqual(logger.msgs[0],
				 ("debug", "Writing to file '%s' the following:\n%s"
				  % (test_path, test_contents)))
		expected_error = create_IOError(errno.EACCES, test_path)
		self.assertEqual(logger.msgs[1],
				 ("debug", "Failed to write to file '%s': %s"
					% (test_path, expected_error)))

	def test_write_with_error_with_log_error(self):
		logger = MockLogger()
		file_ops = MockFileOperations(error_to_raise=errno.EACCES)
		fh = FileHandler(file_ops=file_ops,
				log_func=logger.debug,
				log_error_func=logger.error)
		test_path = 'foo'
		test_contents = 'foo\nbar\n'

		try:
			fh.write(test_path, test_contents)
			self.fail()
		except IOError as e:
			self.assertEqual(e.errno, errno.EACCES)

		self.assertEqual(file_ops.read_called, 0)
		self.assertEqual(file_ops.write_called, 1)
		self.assertEqual(len(logger.msgs), 2)
		self.assertEqual(logger.msgs[0],
				 ("debug", "Writing to file '%s' the following:\n%s"
				  % (test_path, test_contents)))
		expected_error = create_IOError(errno.EACCES, test_path)
		self.assertEqual(logger.msgs[1],
				 ("error", "Failed to write to file '%s': %s"
				  % (test_path, expected_error)))
