class FileOperations(object):
	'''Backend for accessing files on disk.

	This class provides access to files on disk. It should not be used by
	itself. Use FileHandler instead.
	'''
	@staticmethod
	def read(path):
		with open(path, mode="r") as f:
			return f.read()

	@staticmethod
	def write(path, contents):
		with open(path, mode="w") as f:
			f.write(contents)

class FileHandler(object):
	'''File access interface.

	This class is the prefered interface for accessing files in Tuned. It
	allows us to do consistent logging and it is easily mockable - the
	backend for actual reading/writing files can be easily replaced with a
	mock implementation.

	Constructor arguments:
	file_ops  -- backend for file access. Defaults to FileOperations. In
		     tests, override this with tests.unit.lib.MockFileOperations.
	log_func  -- log function that will be used to log all file accesses.
		     Normally, this should be set to log.debug. In tests, you
		     will likely want to leave this unset.
	log_error -- log function that will be used to log errors that happened
		     on file access. If not set, log_func will be used. Normally,
		     this should be set to either log.debug (if you wish to do
		     more high-level error logging yourself) or log.error. In
		     tests, you will likely want to leave this unset.

	Example of use:
	file_handler = FileHandler(log_func=log.debug)
	try:
	    content = file_handler.read(path1)
	    file_handler.write(path2, "foo")
	except IOError:
	    log.error("-- my high-level error message --")

	Example of use in tests:
	file_ops = MockFileOperations()
	file_ops.files["/sys/block/sda/queue/read_ahead_kb"] = "128\n"
	file_handler = FileHandler(file_ops=file_ops)
	logger = MockLogger()
	# MyLib uses file_handler to access files and logger to log high-level
	# log messages.
	lib = MyLib(file_handler, logger)

	res = lib.do_stuff_with_files()

	assert res is None
	assert logger.msgs[0][0] == "error"
	assert "my high-level error" in logger.msgs[0][1]

	'''
	def __init__(self, file_ops=FileOperations,
			log_func=None,
			log_error_func=None):
		self._file_ops = file_ops
		self._log_func = log_func
		self._log_error_func = log_error_func

	def _log(self, msg):
		if self._log_func is not None:
			self._log_func(msg)

	def _log_error(self, msg):
		if self._log_error_func is not None:
			self._log_error_func(msg)
		elif self._log_func is not None:
			self._log_func(msg)

	def read(self, path):
		try:
			self._log("Reading file '%s'" % path)
			contents = self._file_ops.read(path)
			self._log("Contents of the file '%s':\n%s"
					% (path, contents))
			return contents
		except Exception as e:
			self._log_error("Failed to read file '%s': %s"
					% (path, e))
			raise

	def write(self, path, contents):
		try:
			self._log("Writing to file '%s' the following:\n%s"
					% (path, contents))
			self._file_ops.write(path, contents)
			self._log("Finished writing to file '%s"
					% path)
		except Exception as e:
			self._log_error("Failed to write to file '%s': %s"
					% (path, e))
			raise
