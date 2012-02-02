class Plugin(object):
	"""
	Base class for all plugins.

	Plugins change various system settings in order to get desired performance or power
	saving. Plugins use Monitor objects to get information from the running system.

	Methods requiring reimplementation:
	 - update_tuning(self)
	 - tunable_devices(cls)
	"""

	# class methods

	@classmethod
	def _get_default_options(cls):
		return {}

	@classmethod
	def tunable_devices(cls):
		return None

	# instance methods

	def __init__(self, devices = None, options = None):
		self._devices = devices
		self._options = self._get_default_options()
		if options is not None:
			self._merge_options(options)

	def __del__(self):
		try:
			self.cleanup()
		except:
			pass

	def cleanup(self):
		pass

	def _merge_options(self, options):
		for key in options:
			if key in self._options:
				self._options[key] = options[key]

	def update_tuning(self):
		raise NotImplementedError()
