class Plugin(object):
	"""
	Base class for all plugins.

	Plugins change various system settings in order to get desired performance or power
	saving. Plugins use Monitor objects to get information from the running system.

	Methods requiring reimplementation:
	 - update_tuning(self)
	"""

	# class methods

	@classmethod
	def _get_default_options(cls):
		return {}

	@classmethod
	def tunable_devices(cls):
		return None

	@classmethod
	def is_supported(cls):
		return True

	# instance methods

	def __init__(self, devices = [], options = None):
		self._devices = devices
		if not self._devices:
			self._devices = []
		self._commands = {}
		self._options = self._get_default_options()
		self._options["_load_path"] = ""
		if not self._options.has_key("dynamic_tuning"):
			self._options["dynamic_tuning"] = "1"
		if not self._options.has_key("static_tuning"):
			self._options["static_tuning"] = "1"
		if options is not None:
			self._merge_options(options)

	@property
	def dynamic_tuning(self):
		return self._options["dynamic_tuning"] in ["1", "true"]

	@property
	def static_tuning(self):
		return self._options["static_tuning"] in ["1", "true"]

	#def __del__(self):
		#try:
			#self.cleanup()
		#except:
			#pass

	def register_command(self, option, set_fnc, revert_fnc = None, is_per_dev = False):
		self._commands[option] = (is_per_dev, set_fnc, revert_fnc)

	def execute_commands(self):
		for option, (is_per_dev, set_fnc, revert_fnc) in self._commands.iteritems():
			if not self._options.has_key(option):
				continue

			if is_per_dev:
				for dev in self._devices:
					set_fnc(dev, self._options[option])
			else:
				set_fnc(self._options[option])

	def cleanup_commands(self):
		for option, (is_per_dev, set_fnc, revert_fnc) in self._commands.iteritems():
			if not self._options.has_key(option):
				continue

			if revert_fnc:
				set_fnc = revert_fnc

			if is_per_dev:
				for dev in self._devices:
					set_fnc(dev, None)
			else:
				set_fnc(None)

	def cleanup(self):
		pass

	def _merge_options(self, options):
		for key in options:
			if key in self._options:
				self._options[key] = options[key]

	def update_tuning(self):
		raise NotImplementedError()
