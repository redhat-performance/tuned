import tuned.logs
import sys
import traceback

exception_logger = tuned.logs.get()

class TunedException(Exception):
	"""
	"""

	def log(self, logger = None):
		if logger is None:
			logger = exception_logger
		logger.error(str(self))
		self._log_trace(logger)

	def _log_trace(self, logger):
		(exc_type, exc_value, exc_traceback) = sys.exc_info()
		if exc_value != self:
			logger.debug("stack trace is no longer available")
		else:
			exception_info = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)).rstrip()
			logger.debug(exception_info)
