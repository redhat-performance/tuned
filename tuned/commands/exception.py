import tuned.exceptions

class LoadCommandException(tuned.exceptions.TunedException):
	def __init__(self, command_name, inner_exception = None):
		super(self.__class__, self).__init__()
		self._command_name = command_name
		self._inner_exception = inner_exception

	@property
	def command_name(self):
		return self._command_name

	@property
	def inner_exception(self):
		return self._inner_exception

	def __str__(self):
		message = "Unable to load command '%s'" % self._command_name
		if self._inner_exception is not None:
			message += " (%s)" % str(self._inner_exception)

		return message[0].lower() + message[1:]
