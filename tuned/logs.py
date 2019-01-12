import atexit
import logging
import logging.handlers
import os
import os.path
import inspect
import tuned.consts as consts
import random
import string
import threading
try:
	from StringIO import StringIO
except:
	from io import StringIO

__all__ = ["get"]

root_logger = None

log_handlers = {}
log_handlers_lock = threading.Lock()

class LogHandler(object):
	def __init__(self, handler, stream):
		self.handler = handler
		self.stream = stream

def _random_string(length):
	r = random.SystemRandom()
	chars = string.ascii_letters + string.digits
	res = ""
	for i in range(length):
		res += r.choice(chars)
	return res

def log_capture_start(log_level):
	with log_handlers_lock:
		for i in range(10):
			token = _random_string(16)
			if token not in log_handlers:
				break
		else:
			return None
		stream = StringIO()
		handler = logging.StreamHandler(stream)
		handler.setLevel(log_level)
		formatter = logging.Formatter(
				"%(levelname)-8s %(name)s: %(message)s")
		handler.setFormatter(formatter)
		root_logger.addHandler(handler)
		log_handler = LogHandler(handler, stream)
		log_handlers[token] = log_handler
		root_logger.debug("Added log handler %s." % token)
		return token

def log_capture_finish(token):
	with log_handlers_lock:
		try:
			log_handler = log_handlers[token]
		except KeyError:
			return None
		content = log_handler.stream.getvalue()
		log_handler.stream.close()
		root_logger.removeHandler(log_handler.handler)
		del log_handlers[token]
		root_logger.debug("Removed log handler %s." % token)
		return content

def get():
	global root_logger
	if root_logger is None:
		root_logger = logging.getLogger("tuned")

	calling_module = inspect.currentframe().f_back
	name = calling_module.f_locals["__name__"]
	if name == "__main__":
		name = "tuned"
		return root_logger
	elif name.startswith("tuned."):
		(root, child) = name.split(".", 1)
		child_logger = root_logger.getChild(child)
		child_logger.remove_all_handlers()
		child_logger.setLevel("NOTSET")
		return child_logger
	else:
		assert False

class TunedLogger(logging.getLoggerClass()):
	"""Custom tuned daemon logger class."""
	_formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
	_console_handler = None
	_file_handler = None

	def __init__(self, *args, **kwargs):
		super(TunedLogger, self).__init__(*args, **kwargs)
		self.setLevel(logging.INFO)
		self.switch_to_console()

	def console(self, msg, *args, **kwargs):
		self.log(consts.LOG_LEVEL_CONSOLE, msg, *args, **kwargs)

	def switch_to_console(self):
		self._setup_console_handler()
		self.remove_all_handlers()
		self.addHandler(self._console_handler)

	def switch_to_file(self, filename = consts.LOG_FILE, 
			   maxBytes = consts.LOG_FILE_MAXBYTES,
			   backupCount = consts.LOG_FILE_COUNT):
		self._setup_file_handler(filename, maxBytes, backupCount)
		self.remove_all_handlers()
		self.addHandler(self._file_handler)

	def remove_all_handlers(self):
		_handlers = self.handlers
		for handler in _handlers:
			self.removeHandler(handler)

	@classmethod
	def _setup_console_handler(cls):
		if cls._console_handler is not None:
			return

		cls._console_handler = logging.StreamHandler()
		cls._console_handler.setFormatter(cls._formatter)

	@classmethod
	def _setup_file_handler(cls, filename, maxBytes, backupCount):
		if cls._file_handler is not None:
			return

		log_directory = os.path.dirname(filename)
		if log_directory == '':
			log_directory = '.'
		if not os.path.exists(log_directory):
			os.makedirs(log_directory)

		cls._file_handler = logging.handlers.RotatingFileHandler(
			filename, maxBytes = int(maxBytes), backupCount = int(backupCount))
		cls._file_handler.setFormatter(cls._formatter)

logging.addLevelName(consts.LOG_LEVEL_CONSOLE, consts.LOG_LEVEL_CONSOLE_NAME)
logging.setLoggerClass(TunedLogger)
atexit.register(logging.shutdown)
