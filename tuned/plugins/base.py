import re
import tuned.consts as consts
import tuned.profiles.variables
import tuned.logs
import collections
from tuned.utils.commands import commands
import os
from subprocess import Popen, PIPE

log = tuned.logs.get()

class Plugin(object):
	"""
	Base class for all plugins.

	Plugins change various system settings in order to get desired performance or power
	saving. Plugins use Monitor objects to get information from the running system.

	Intentionally a lot of logic is included in the plugin to increase plugin flexibility.
	"""

	def __init__(self, monitors_repository, storage_factory, hardware_inventory, device_matcher, device_matcher_udev, instance_factory, global_cfg, variables):
		"""Plugin constructor."""

		self._storage = storage_factory.create(self.__class__.__name__)
		self._monitors_repository = monitors_repository
		self._hardware_inventory = hardware_inventory
		self._device_matcher = device_matcher
		self._device_matcher_udev = device_matcher_udev
		self._instance_factory = instance_factory

		self._instances = collections.OrderedDict()
		self._init_commands()
		self._init_devices()

		self._global_cfg = global_cfg
		self._variables = variables
		self._has_dynamic_options = False

		self._options_used_by_dynamic = self._get_config_options_used_by_dynamic()

		self._cmd = commands()

	def cleanup(self):
		self.destroy_instances()

	@property
	def name(self):
		return self.__class__.__module__.split(".")[-1].split("_", 1)[1]

	#
	# Plugin configuration manipulation and helpers.
	#

	@classmethod
	def _get_config_options(self):
		"""Default configuration options for the plugin."""
		return {}

	@classmethod
	def _get_config_options_used_by_dynamic(self):
		"""List of config options used by dynamic tuning. Their previous values will be automatically saved and restored."""
		return []

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

	#
	# Interface for manipulation with instances of the plugin.
	#

	def create_instance(self, name, devices_expression, devices_udev_regex, script_pre, script_post, options):
		"""Create new instance of the plugin and seize the devices."""
		if name in self._instances:
			raise Exception("Plugin instance with name '%s' already exists." % name)

		effective_options = self._get_effective_options(options)
		instance = self._instance_factory.create(self, name, devices_expression, devices_udev_regex, \
			script_pre, script_post, effective_options)
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

	def initialize_instance(self, instance):
		"""Initialize an instance."""
		log.debug("initializing instance %s (%s)" % (instance.name, self.name))
		self._instance_init(instance)

	def destroy_instances(self):
		"""Destroy all instances."""
		for instance in list(self._instances.values()):
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
		self._devices_supported = False
		self._assigned_devices = set()
		self._free_devices = set()

	def _get_device_objects(self, devices):
		"""Override this in a subclass to transform a list of device names (e.g. ['sda'])
		   to a list of pyudev.Device objects, if your plugin supports it"""
		return None

	def _get_matching_devices(self, instance, devices):
		if instance.devices_udev_regex is None:
			return set(self._device_matcher.match_list(instance.devices_expression, devices))
		else:
			udev_devices = self._get_device_objects(devices)
			if udev_devices is None:
				log.error("Plugin '%s' does not support the 'devices_udev_regex' option", self.name)
				return set()
			udev_devices = self._device_matcher_udev.match_list(instance.devices_udev_regex, udev_devices)
			return set([x.sys_name for x in udev_devices])

	def assign_free_devices(self, instance):
		if not self._devices_supported:
			return

		log.debug("assigning devices to instance %s" % instance.name)
		to_assign = self._get_matching_devices(instance, self._free_devices)
		instance.active = len(to_assign) > 0
		if not instance.active:
			log.warn("instance %s: no matching devices available" % instance.name)
		else:
			name = instance.name
			if instance.name != self.name:
				name += " (%s)" % self.name
			log.info("instance %s: assigning devices %s" % (name, ", ".join(to_assign)))
			instance.devices.update(to_assign) # cannot use |=
			self._assigned_devices |= to_assign
			self._free_devices -= to_assign

	def release_devices(self, instance):
		if not self._devices_supported:
			return

		to_release = instance.devices & self._assigned_devices

		instance.active = False
		instance.devices.clear()
		self._assigned_devices -= to_release
		self._free_devices |= to_release

	#
	# Tuning activation and deactivation.
	#

	def _run_for_each_device(self, instance, callback):
		if self._devices_supported:
			devices = instance.devices
		else:
			devices = [None, ]

		for device in devices:
			callback(instance, device)

	def _instance_pre_static(self, instance, enabling):
		pass

	def _instance_post_static(self, instance, enabling):
		pass

	def _call_device_script(self, instance, script, op, devices, full_rollback = False):
		if script is None:
			return None
		if len(devices) == 0:
			log.warn("Instance '%s': no device to call script '%s' for." % (instance.name, script))
			return None
		if not script.startswith("/"):
			log.error("Relative paths cannot be used in script_pre or script_post. " \
				+ "Use ${i:PROFILE_DIR}.")
			return False
		dir_name = os.path.dirname(script)
		ret = True
		for dev in devices:
			environ = os.environ
			environ.update(self._variables.get_env())
			arguments = [op]
			if full_rollback:
				arguments.append("full_rollback")
			arguments.append(dev)
			log.info("calling script '%s' with arguments '%s'" % (script, str(arguments)))
			log.debug("using environment '%s'" % str(list(environ.items())))
			try:
				proc = Popen([script] +  arguments, \
						stdout=PIPE, stderr=PIPE, \
						close_fds=True, env=environ, \
						cwd = dir_name, universal_newlines = True)
				out, err = proc.communicate()
				if proc.returncode:
					log.error("script '%s' error: %d, '%s'" % (script, proc.returncode, err[:-1]))
					ret = False
			except (OSError,IOError) as e:
				log.error("script '%s' error: %s" % (script, e))
				ret = False
		return ret

	def instance_apply_tuning(self, instance):
		"""
		Apply static and dynamic tuning if the plugin instance is active.
		"""
		if not instance.active:
			return

		if instance.has_static_tuning:
			self._call_device_script(instance, instance.script_pre, "apply", instance.devices)
			self._instance_pre_static(instance, True)
			self._instance_apply_static(instance)
			self._instance_post_static(instance, True)
			self._call_device_script(instance, instance.script_post, "apply", instance.devices)
		if instance.has_dynamic_tuning and self._global_cfg.get(consts.CFG_DYNAMIC_TUNING, consts.CFG_DEF_DYNAMIC_TUNING):
			self._run_for_each_device(instance, self._instance_apply_dynamic)

	def instance_verify_tuning(self, instance, ignore_missing):
		"""
		Verify static tuning if the plugin instance is active.
		"""
		if not instance.active:
			return None

		if instance.has_static_tuning:
			if self._call_device_script(instance, instance.script_pre, "verify", instance.devices) == False:
				return False
			if self._instance_verify_static(instance, ignore_missing) == False:
				return False
			if self._call_device_script(instance, instance.script_post, "verify", instance.devices) == False:
				return False
			return True
		else:
			return None

	def instance_update_tuning(self, instance):
		"""
		Apply dynamic tuning if the plugin instance is active.
		"""
		if not instance.active:
			return
		if instance.has_dynamic_tuning and self._global_cfg.get(consts.CFG_DYNAMIC_TUNING, consts.CFG_DEF_DYNAMIC_TUNING):
			self._run_for_each_device(instance, self._instance_update_dynamic)

	def instance_unapply_tuning(self, instance, full_rollback = False):
		"""
		Remove all tunings applied by the plugin instance.
		"""
		if instance.has_dynamic_tuning and self._global_cfg.get(consts.CFG_DYNAMIC_TUNING, consts.CFG_DEF_DYNAMIC_TUNING):
			self._run_for_each_device(instance, self._instance_unapply_dynamic)
		if instance.has_static_tuning:
			self._call_device_script(instance, instance.script_post, "unapply", instance.devices, full_rollback = full_rollback)
			self._instance_pre_static(instance, False)
			self._instance_unapply_static(instance, full_rollback)
			self._instance_post_static(instance, False)
			self._call_device_script(instance, instance.script_pre, "unapply", instance.devices, full_rollback = full_rollback)

	def _instance_apply_static(self, instance):
		self._execute_all_non_device_commands(instance)
		self._execute_all_device_commands(instance, instance.devices)

	def _instance_verify_static(self, instance, ignore_missing):
		ret = True
		if self._verify_all_non_device_commands(instance, ignore_missing) == False:
			ret = False
		if self._verify_all_device_commands(instance, instance.devices, ignore_missing) == False:
			ret = False
		return ret

	def _instance_unapply_static(self, instance, full_rollback = False):
		self._cleanup_all_device_commands(instance, instance.devices)
		self._cleanup_all_non_device_commands(instance)

	def _instance_apply_dynamic(self, instance, device):
		for option in [opt for opt in self._options_used_by_dynamic if self._storage_get(instance, self._commands[opt], device) is None]:
			self._check_and_save_value(instance, self._commands[option], device)

		self._instance_update_dynamic(instance, device)

	def _instance_unapply_dynamic(self, instance, device):
		raise NotImplementedError()

	def _instance_update_dynamic(self, instance, device):
		raise NotImplementedError()

	#
	# Registration of commands for static plugins.
	#

	def _init_commands(self):
		"""
		Initialize commands.
		"""
		self._commands = collections.OrderedDict()
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
				info["priority"] = member._command["priority"]
			elif "get" in member._command:
				info["get"] = member
			elif "custom" in member._command:
				info["custom"] = member
				info["per_device"] = member._command["per_device"]
				info["priority"] = member._command["priority"]

			self._commands[command_name] = info

		# sort commands by priority
		self._commands = collections.OrderedDict(sorted(iter(self._commands.items()), key=lambda name_info: name_info[1]["priority"]))

	def _check_commands(self):
		"""
		Check if all commands are defined correctly.
		"""
		for command_name, command in list(self._commands.items()):
			# do not check custom commands
			if command.get("custom", False):
				continue
			# automatic commands should have 'get' and 'set' functions
			if "get" not in command or "set" not in command:
				raise TypeError("Plugin command '%s' is not defined correctly" % command_name)

	#
	# Operations with persistent storage for status data.
	#

	def _storage_key(self, instance_name = None, command_name = None,
			device_name = None):
		class_name = type(self).__name__
		instance_name = "" if instance_name is None else instance_name
		command_name = "" if command_name is None else command_name
		device_name = "" if device_name is None else device_name
		return "%s/%s/%s/%s" % (class_name, instance_name,
				command_name, device_name)

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
	# Command execution, verification, and cleanup.
	#

	def _execute_all_non_device_commands(self, instance):
		for command in [command for command in list(self._commands.values()) if not command["per_device"]]:
			new_value = self._variables.expand(instance.options.get(command["name"], None))
			if new_value is not None:
				self._execute_non_device_command(instance, command, new_value)

	def _execute_all_device_commands(self, instance, devices):
		for command in [command for command in list(self._commands.values()) if command["per_device"]]:
			new_value = self._variables.expand(instance.options.get(command["name"], None))
			if new_value is None:
				continue
			for device in devices:
				self._execute_device_command(instance, command, device, new_value)

	def _verify_all_non_device_commands(self, instance, ignore_missing):
		ret = True
		for command in [command for command in list(self._commands.values()) if not command["per_device"]]:
			new_value = self._variables.expand(instance.options.get(command["name"], None))
			if new_value is not None:
				if self._verify_non_device_command(instance, command, new_value, ignore_missing) == False:
					ret = False
		return ret

	def _verify_all_device_commands(self, instance, devices, ignore_missing):
		ret = True
		for command in [command for command in list(self._commands.values()) if command["per_device"]]:
			new_value = instance.options.get(command["name"], None)
			if new_value is None:
				continue
			for device in devices:
				if self._verify_device_command(instance, command, device, new_value, ignore_missing) == False:
					ret = False
		return ret

	def _process_assignment_modifiers(self, new_value, current_value):
		if new_value is not None:
			nws = str(new_value)
			if len(nws) <= 1:
				return new_value
			op = nws[:1]
			val = nws[1:]
			if current_value is None:
				return val if op in ["<", ">"] else new_value
			try:
				if op == ">":
					if int(val) > int(current_value):
						return val
					else:
						return None
				elif op == "<":
					if int(val) < int(current_value):
						return val
					else:
						return None
			except ValueError:
				log.warn("cannot compare new value '%s' with current value '%s' by operator '%s', using '%s' directly as new value" % (val, current_value, op, new_value))
		return new_value

	def _get_current_value(self, command, device = None, ignore_missing=False):
		if device is not None:
			return command["get"](device, ignore_missing=ignore_missing)
		else:
			return command["get"]()

	def _check_and_save_value(self, instance, command, device = None, new_value = None):
		current_value = self._get_current_value(command, device)
		new_value = self._process_assignment_modifiers(new_value, current_value)
		if new_value is not None and current_value is not None:
			self._storage_set(instance, command, current_value, device)
		return new_value

	def _execute_device_command(self, instance, command, device, new_value):
		if command["custom"] is not None:
			command["custom"](True, new_value, device, False, False)
		else:
			new_value = self._check_and_save_value(instance, command, device, new_value)
			if new_value is not None:
				command["set"](new_value, device, sim = False)

	def _execute_non_device_command(self, instance, command, new_value):
		if command["custom"] is not None:
			command["custom"](True, new_value, False, False)
		else:
			new_value = self._check_and_save_value(instance, command, None, new_value)
			if new_value is not None:
				command["set"](new_value, sim = False)

	def _norm_value(self, value):
		v = self._cmd.unquote(str(value))
		if re.match(r'\s*(0+,?)+([\da-fA-F]*,?)*\s*$', v):
			return re.sub(r'^\s*(0+,?)+', "", v)
		return v

	def _verify_value(self, name, new_value, current_value, ignore_missing, device = None):
		if new_value is None:
			return None
		ret = False
		if current_value is None and ignore_missing:
			if device is None:
				log.info(consts.STR_VERIFY_PROFILE_VALUE_MISSING % name)
			else:
				log.info(consts.STR_VERIFY_PROFILE_DEVICE_VALUE_MISSING % (device, name))
			return True

		if current_value is not None:
			current_value = self._norm_value(current_value)
			new_value = self._norm_value(new_value)
			try:
				ret = int(new_value) == int(current_value)
			except ValueError:
				try:
					ret = int(new_value, 16) == int(current_value, 16)
				except ValueError:
					ret = str(new_value) == str(current_value)
					if not ret:
						vals = str(new_value).split('|')
						for val in vals:
							val = val.strip()
							ret = val == current_value
							if ret:
								break
		if ret:
			if device is None:
				log.info(consts.STR_VERIFY_PROFILE_VALUE_OK % (name, str(current_value).strip()))
			else:
				log.info(consts.STR_VERIFY_PROFILE_DEVICE_VALUE_OK % (device, name, str(current_value).strip()))
			return True
		else:
			if device is None:
				log.error(consts.STR_VERIFY_PROFILE_VALUE_FAIL % (name, str(current_value).strip(), str(new_value).strip()))
			else:
				log.error(consts.STR_VERIFY_PROFILE_DEVICE_VALUE_FAIL % (device, name, str(current_value).strip(), str(new_value).strip()))
			return False

	def _verify_device_command(self, instance, command, device, new_value, ignore_missing):
		if command["custom"] is not None:
			return command["custom"](True, new_value, device, True, ignore_missing)
		current_value = self._get_current_value(command, device, ignore_missing=ignore_missing)
		new_value = self._process_assignment_modifiers(new_value, current_value)
		if new_value is None:
			return None
		new_value = command["set"](new_value, device, True)
		return self._verify_value(command["name"], new_value, current_value, ignore_missing, device)

	def _verify_non_device_command(self, instance, command, new_value, ignore_missing):
		if command["custom"] is not None:
			return command["custom"](True, new_value, True, ignore_missing)
		current_value = self._get_current_value(command)
		new_value = self._process_assignment_modifiers(new_value, current_value)
		if new_value is None:
			return None
		new_value = command["set"](new_value, True)
		return self._verify_value(command["name"], new_value, current_value, ignore_missing)

	def _cleanup_all_non_device_commands(self, instance):
		for command in reversed([command for command in list(self._commands.values()) if not command["per_device"]]):
			if (instance.options.get(command["name"], None) is not None) or (command["name"] in self._options_used_by_dynamic):
				self._cleanup_non_device_command(instance, command)

	def _cleanup_all_device_commands(self, instance, devices):
		for command in reversed([command for command in list(self._commands.values()) if command["per_device"]]):
			if (instance.options.get(command["name"], None) is not None) or (command["name"] in self._options_used_by_dynamic):
				for device in devices:
					self._cleanup_device_command(instance, command, device)

	def _cleanup_device_command(self, instance, command, device):
		if command["custom"] is not None:
			command["custom"](False, None, device, False, False)
		else:
			old_value = self._storage_get(instance, command, device)
			if old_value is not None:
				command["set"](old_value, device, sim = False)
			self._storage_unset(instance, command, device)

	def _cleanup_non_device_command(self, instance, command):
		if command["custom"] is not None:
			command["custom"](False, None, False, False)
		else:
			old_value = self._storage_get(instance, command)
			if old_value is not None:
				command["set"](old_value, sim = False)
			self._storage_unset(instance, command)
