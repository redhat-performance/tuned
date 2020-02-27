import errno
import os

def create_IOError(error_code, file_path):
	return IOError(error_code, "%s: '%s'"
			% (os.strerror(error_code), file_path))

class MockFileOperations(object):
	def __init__(self, error_to_raise=None):
		self.files = {}
		self.read_called = 0
		self.write_called = 0
		self.error_to_raise = error_to_raise

	def read(self, path):
		self.read_called += 1
		if self.error_to_raise is not None:
			raise create_IOError(self.error_to_raise, path)
		try:
			return self.files[path]
		except KeyError:
			raise create_IOError(errno.ENOENT, path)

	def write(self, path, contents):
		self.write_called += 1
		if self.error_to_raise is not None:
			raise create_IOError(self.error_to_raise, path)
		self.files[path] = contents

class MockLogger(object):
	def __init__(self):
		self.msgs = []

	def debug(self, msg):
		self.msgs.append(("debug", msg))

	def info(self, msg):
		self.msgs.append(("info", msg))

	def warn(self, msg):
		self.msgs.append(("warn", msg))

	def error(self, msg):
		self.msgs.append(("error", msg))
