class Plugin(object):
	@classmethod
	def _get_default_options(cls):
		return {}

	def __init__(self, options = None):
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
