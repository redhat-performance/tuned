import tuned.logs

log = tuned.logs.get()

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

	def __init__(self, monitors_repository, storage_factory, devices=None, options=None):
		"""
		Plugin instance constructor. Plugins should not override this function in general,
		_post_init method should be used instead.
		"""
		self._monitors_repository = monitors_repository
		self._storage = storage_factory.create(self.__class__.__name__)
		self._devices = devices
		self._options = self._get_default_options()
		if options is not None:
			self._merge_options(options)
		self._dynamic_tuning = True

		self._init_commands()
		self._post_init()

	def _init_commands(self):
		self._commands = {}
		self._autoregister_commands()

		for command_name, command in self._commands.iteritems():
			if "get" not in command or "set" not in command:
				raise TypeError("Plugin command '%s' is not defined correctly" % command_name)

	def _post_init(self):
		pass

	@property
	def dynamic_tuning(self):
		return self._dynamic_tuning

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

			self._commands[command_name] = info

	def _storage_key(self, command_name, device=None):
		if device is not None:
			return "%s@%s" % (command_name, device)
		else:
			return command_name

	def _execute_command(self, command_name, command):
		if not self._options.has_key(command_name):
			raise ValueError("Command is not supported.")

		new_value = self._options[command_name]
		if new_value is None:
			return

		if not command["per_device"]:
			current_value = command["get"]()
			storage_key = self._storage_key(command_name)
			self._storage.set(command_name, current_value)
			command["set"](new_value)
			return

		if self._devices is None:
			raise TypeError("No devices were specified.")

		for device in self._devices:
			current_value = command["get"](device)
			storage_key = self._storage_key(command_name, device)
			self._storage.set(storage_key, current_value)
			command["set"](new_value, device)

	def _cleanup_command(self, command_name, command):
		if not self._options.has_key(command_name):
			raise ValueError("Command is not supported.")

		if self._options[command_name] is None:
			return

		if not command["per_device"]:
			storage_key = self._storage_key(command_name)
			old_value = self._storage.get(storage_key)
			command["set"](old_value)
			self._storage.unset(storage_key)
			return

		if self._devices is None:
			raise TypeError("No devices were specified.")

		for device in self._devices:
			storage_key = self._storage_key(command_name, device)
			old_value = self._storage.get(storage_key)
			command["set"](old_value, device)
			self._storage.unset(storage_key)

	def execute_commands(self):
		for command_name, command in self._commands.iteritems():
			self._execute_command(command_name, command)

	def cleanup_commands(self):
		for command_name, command in self._commands.iteritems():
			self._cleanup_command(command_name, command)

	def cleanup(self):
		pass

	def _merge_options(self, options):
		for key in options:
			if key in self._options:
				self._options[key] = options[key]
			else:
				log.warn("Unknown option '%s' for plugin '%s'." % (key, self.__class__.__name__))

	def update_tuning(self):
		raise NotImplementedError()

	def _option_bool(self, value):
		if type(value) is bool:
			return value
		value = str(value).lower()
		return value == "true" or value == "1"

	def _config_bool(self, value, true_value="1", false_value="0"):
		if value == True or value == "1" or value.lower() == "true":
			return true_value
		elif value == False or value == "0" or value.lower() == "false":
			return false_value
		else:
			return None
