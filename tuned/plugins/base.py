import tuned.logs
import collections

log = tuned.logs.get()

class Plugin(object):
	"""
	Base class for all plugins.

	Plugins change various system settings in order to get desired performance or power
	saving. Plugins use Monitor objects to get information from the running system.

	Intentionally a lot of logic is included in the plugin to increase plugin flexibility.
	"""

	def __init__(self, monitors_repository, storage_factory, hardware_inventory, device_matcher, instance_factory):
		"""Plugin constructor."""

		self._storage = storage_factory.create(self.__class__.__name__)
		self._monitors_repository = monitors_repository
		self._hardware_inventory = hardware_inventory
		self._device_matcher = device_matcher
		self._instance_factory = instance_factory

		self._instances = collections.OrderedDict()
		self._init_commands()
		self._init_devices()

		self._has_dynamic_options = False

	def cleanup(self):
		self.destroy_instances()

	@property
	def name(self):
		return self.__class__.__module__.split(".")[-1].lstrip("plugin_")

	#
	# Plugin configuration manipulation and helpers.
	#

	def _get_config_options(self):
		"""Default configuration options for the plugin."""
		return {}

	def _get_effective_options(self, options):
		"""Merge provided options with plugin default options."""
		# TODO: _has_dynamic_options is a hack
		effective = self._get_config_options().copy()
		for key in options:
			if key in effective or self._has_dynamic_options:
				effective[key] = options[key]
			else:
				log.warn("Unknown option '%s' for plugin '%s'." % (key, self.__class__.__name__))
		return effective

	def _option_bool(self, value):
		if type(value) is bool:
			return value
		value = str(value).lower()
		return value == "true" or value == "1"

	def _config_bool(self, value, true_value="1", false_value="0"):
		if value == True or value == "1" or str(value).lower() == "true":
			return true_value
		elif value == False or value == "0" or str(value).lower() == "false":
			return false_value
		else:
			return None

	#
	# Interface for manipulation with instances of the plugin.
	#

	def create_instance(self, name, devices_expression, options):
		"""Create new instance of the plugin and seize the devices."""
		if name in self._instances:
			raise Exception("Plugin instance with name '%s' already exists." % name)

		effective_options = self._get_effective_options(options)
		instance = self._instance_factory.create(self, name, devices_expression, effective_options)
		self._instances[name] = instance

		return instance

	def destroy_instance(self, instance):
		"""Destroy existing instance."""
		if instance._plugin != self:
			raise Exception("Plugin instance '%s' does not belong to this plugin '%s'." % (instance, self))
		if instance.name not in self._instances:
			raise Exception("Plugin instance '%s' was already destroyed." % instance)

		instance = self._instances[instance.name]
		self._destroy_instance(instance)
		del self._instances[instance.name]

	def initialize_instances(self):
		"""Initialize all created instances."""
		for (instance_name, instance) in self._instances.items():
			log.debug("initializing instance %s (%s)" % (instance_name, self.name))
			self._instance_init(instance)

	def destroy_instances(self):
		"""Destroy all instances."""
		for instance in self._instances.values():
			log.debug("destroying instance %s (%s)" % (instance.name, self.name))
			self._destroy_instance(instance)
		self._instances.clear()

	def _destroy_instance(self, instance):
		self.release_devices(instance)
		self._instance_cleanup(instance)

	def _instance_init(self, instance):
		raise NotImplementedError()

	def _instance_cleanup(self, instance):
		raise NotImplementedError()

	#
	# Devices handling
	#

	def _init_devices(self):
		self._devices = None
		self._assigned_devices = set()
		self._free_devices = set()

	def _assign_free_devices_to_instance(self, instance):
		# devices are not supported
		if self._devices is None:
			return

		assert(isinstance(self._devices, set))
		assert(isinstance(self._assigned_devices, set))
		assert(isinstance(self._free_devices, set))

		to_assign = set(self._device_matcher.match_list(instance.devices_expression, self._free_devices))

		if len(to_assign) == 0:
			log.warn("instance '%s': no matching devices available" % instance.name)
			instance.active = False
			return

		log.info("instance '%s': assigning devices %s" % (instance.name, ", ".join(to_assign)))

		instance.active = True
		instance.devices.update(to_assign) # cannot use |=
		self._assigned_devices |= to_assign
		self._free_devices -= to_assign

	def assign_free_devices(self):
		log.debug("assigning devices to all instances")
		for instance in reversed(self._instances):
			self._assign_free_devices_to_instance(self._instances[instance])

	def release_devices(self, instance):
		# devices are not supported
		if self._devices is None:
			return

		to_release = instance.devices & self._devices

		instance.active = False
		instance.devices.clear()
		self._assigned_devices -= to_release
		self._free_devices |= to_release

	#
	# Tuning activation and deactivation.
	#

	def instance_apply_tuning(self, instance):
		"""
		Apply static and dynamic tuning if the plugin instance is active.
		"""
		if not instance.active:
			return
		if instance.has_static_tuning:
			self._instance_apply_static(instance)
		if instance.has_dynamic_tuning:
			self._instance_update_dynamic(instance)

	def instance_update_tuning(self, instance):
		"""
		Apply dynamic tuning if the plugin instance is active.
		"""
		if not instance.active:
			return
		if instance.has_dynamic_tuning:
			self._instance_update_dynamic(instance)

	def instance_unapply_tuning(self, instance):
		"""
		Remove all tunings applied by the plugin instance.
		"""
		if instance.has_dynamic_tuning:
			self._instance_unapply_dynamic(instance)
		if instance.has_static_tuning:
			self._instance_unapply_static(instance)


	def _instance_apply_static(self, instance):
		for command in self._commands.values():
			self._execute_command(instance, command)

	def _instance_unapply_static(self, instance):
		for command in self._commands.values():
			self._cleanup_command(instance, command)

	def _instance_apply_dynamic(self, instance):
		raise NotImplementedError()

	def _instance_unapply_dynamic(self, instance):
		raise NotImplementedError()

	def _instance_update_dynamic(self, instance):
		raise NotImplementedError()

	#
	# Registration of commands for static plugins.
	#

	def _init_commands(self):
		"""
		Initialize commands.
		"""
		self._commands = {}
		self._autoregister_commands()
		self._check_commands()

	def _autoregister_commands(self):
		"""
		Register all commands marked using @command_set, @command_get, and @command_custom decorators.
		"""
		for member_name in self.__class__.__dict__:
			if member_name.startswith("__"):
				continue
			member = getattr(self, member_name)
			if not hasattr(member, "_command"):
				continue

			command_name = member._command["name"]
			info = self._commands.get(command_name, {"name": command_name})

			if "set" in member._command:
				info["custom"] = None
				info["set"] = member
				info["per_device"] = member._command["per_device"]
			elif "get" in member._command:
				info["get"] = member
			elif "custom" in member._command:
				info["custom"] = member
				info["per_device"] = member._command["per_device"]

			self._commands[command_name] = info

	def _check_commands(self):
		"""
		Check if all commands are defined correctly.
		"""
		for command_name, command in self._commands.iteritems():
			# do not check custom commands
			if command.get("custom", False):
				continue
			# automatic commands should have 'get' and 'set' functions
			if "get" not in command or "set" not in command:
				raise TypeError("Plugin command '%s' is not defined correctly" % command_name)

	#
	# Operations with persistent storage for status data.
	#

	def _storage_key(self, instance_name, command_name, device_name=None):
		if device_name is not None:
			return "%s/%s/%s" % (command_name, instance_name, device_name)
		else:
			return "%s/%s" % (command_name, instance_name)

	def _storage_set(self, instance, command, value, device_name=None):
		key = self._storage_key(instance.name, command["name"], device_name)
		self._storage.set(key, value)

	def _storage_get(self, instance, command, device_name=None):
		key = self._storage_key(instance.name, command["name"], device_name)
		return self._storage.get(key)

	def _storage_unset(self, instance, command, device_name=None):
		key = self._storage_key(instance.name, command["name"], device_name)
		return self._storage.unset(key)

	#
	# Command execution and cleanup.
	#

	def _execute_command(self, instance, command):
		new_value = instance.options.get(command["name"], None)
		if new_value is None:
			return

		if command["per_device"]:
			for device in instance.devices:
				self._execute_device_command(instance, command, device, new_value)
		else:
			self._execute_non_device_command(instance, command, new_value)

	def _execute_device_command(self, instance, command, device, new_value):
		if command["custom"] is not None:
			command["custom"](True, new_value, device)
		else:
			current_value = command["get"](device)
			self._storage_set(instance, command, current_value, device)
			command["set"](new_value, device)

	def _execute_non_device_command(self, instance, command, new_value):
		if command["custom"] is not None:
			command["custom"](True, new_value)
		else:
			current_value = command["get"]()
			self._storage_set(instance, command_name, current_value)
			command["set"](new_value)

	def _cleanup_command(self, instance, command):
		if instance.options.get(command["name"], None) is None:
			return

		if command["per_device"]:
			for device in instance.devices:
				self._cleanup_device_command(instance, command, device)
		else:
			self._cleanup_non_device_command(instance, command)

	def _cleanup_device_command(self, instance, command, device):
		if command["custom"] is not None:
			command["custom"](False, None, device)
		else:
			old_value = self._storage_get(instance, command, device)
			if old_value is not None:
				command["set"](old_value, device)
			self._storage_unset(instance, command, device)

	def _cleanup_non_device_command(self, instance, command):
		if command["custom"] is not None:
			command["custom"](False, None)
		else:
			old_value = self._storage_get(instance, command)
			if old_value is not None:
				command["set"](old_value)
			self._storage_unset(instance, command)
