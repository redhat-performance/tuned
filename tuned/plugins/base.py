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

		# TODO: cannot be injected now
		self._storage = tuned.utils.storage.Storage.get_instance()

		self._autoregister_commands()
		assert self._commands_are_valid()

	@property
	def dynamic_tuning(self):
		return self._options["dynamic_tuning"] in ["1", "true"]

	@property
	def static_tuning(self):
		return self._options["static_tuning"] in ["1", "true"]

	def _autoregister_commands(self):
		"""
		Register all commands marked using @command_set and @command_get decorators.
		"""

		for member_name in self.__class__.__dict__:
			if member_name.startswith("__"):
				continue
			member = getattr(self, member_name)
			if not hasattr(member, "_command"):
				continue

			command_name = member._command["name"]
			info = self._commands.get(command_name, {})

			if "set" in member._command:
				info["set"] = member
				info["per_device"] = member._command["per_device"]
			elif "get" in member._command:
				info["get"] = member

			self._commands["command_name"] = info

	def _commands_are_valid(self):
		for command in commands:
			if "get" not in command or "set" not in command:
				return False
		return True

	# TODO: should be in storage class
	def _storage_key(self, command_name, device):
		if device is not None:
			return "%s@%s" % [command_name, device]
		else:
			return command_name

	# TODO: should be in storage class
	def _storage_get(self, command_name, device = None):
		if not self._storage.data.has_key(self.__class__):
			return None
		key = self._storage_key(command_name, device)
		return self._storage.data[self.__class__].get(key, None)

	# TODO: should be in storage class
	def _storage_set(self, value, command_name, device = None):
		self._storage.data.setdefault(self.__class__, [])
		key = self._storage_key(command_name, device)
		self._storage.data[self.__class__][key] = value

	# TODO: should be in storage class
	def _storage_remove(self, command_name, device = None):
		self._storage.data.setdefault(self.__class__, [])
		key = self._storage_key(command_name, device)
		del self._storage.data[self.__class__][key]

	def execute_commands(self):
		for command_name, command in self._commands.iteritems():
			if not self._options.has_key(command_name):
				continue

			new_value = self._options[command_name]

			# TODO: refactor
			if command["per_device"]:
				for device in self._devices:
					current_value = command["get"](device)
					self._storage_set(current_value, command_name, device)
					command["set"](new_value, device)
			else:
				current_value = command["get"]()
				self._storage_set(current_valuie, command_name)
				command["set"](new_value)

	def cleanup_commands(self):
		for command_name, command in self._commands.iteritems():
			if not self._options.has_key(option):
				continue

			# TODO: refactor
			if command["per_device"]:
				for device in self._devices:
					old_value = self._storage_get(command_name, device)
					if old_value is not None:
						command["set"](old_value, device)
						self._storage_remove(command_name, device)
			else:
				old_value = self._storage_get(command_name)
				if old_value is not None:
					commad["set"](old_value)
					self._storage_remove(command_name)

	def cleanup(self):
		pass

	def _merge_options(self, options):
		for key in options:
			if key in self._options:
				self._options[key] = options[key]

	def update_tuning(self):
		raise NotImplementedError()

	def _config_bool(value, true_value="1", false_value="0"):
		if value == True or value == "1" or value.lower() == "true":
			return true_value
		elif value == False or value == "0" or value.lower() == "false":
			return false_value
		else:
			return None
