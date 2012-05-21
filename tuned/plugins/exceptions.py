import tuned.exceptions

class LoadPluginException(tuned.exceptions.TunedException):
	def __init__(self, plugin_name, inner_exception = None):
		super(self.__class__, self).__init__()
		self._plugin_name = plugin_name
		self._inner_exception = inner_exception

	@property
	def plugin_name(self):
		return self._plugin_name

	@property
	def inner_exception(self):
		return self._inner_exception

	def __str__(self):
		message = "Unable to load plugin '%s'" % self._plugin_name
		if self._inner_exception is not None:
			message += " (%s)" % str(self._inner_exception)

		return message[0].lower() + message[1:]
