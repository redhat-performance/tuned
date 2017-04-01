import collections
import tuned.exceptions
import tuned.logs
import tuned.plugins.exceptions
import tuned.consts as consts

log = tuned.logs.get()

__all__ = ["Manager"]

class Manager(object):
	"""
	Manager creates plugin instances and keeps a track of them.
	"""

	def __init__(self, plugins_repository, monitors_repository, def_instance_priority):
		super(self.__class__, self).__init__()
		self._plugins_repository = plugins_repository
		self._monitors_repository = monitors_repository
		self._def_instance_priority = def_instance_priority
		self._instances = []
		self._plugins = []

	@property
	def plugins(self):
		return self._plugins

	@property
	def instances(self):
		return self._instances

	def create(self, instances_config):
		instance_info_list = []
		for instance_name, instance_info in instances_config.items():
			if not instance_info.enabled:
				log.debug("skipping disabled instance '%s'" % instance_name)
				continue
			instance_info.options.setdefault("priority", self._def_instance_priority)
			instance_info.options["priority"] = int(instance_info.options["priority"])
			instance_info_list.append(instance_info)

		instance_info_list.sort(key=lambda x: x.options["priority"])
		plugins_by_name = collections.OrderedDict()
		for instance_info in instance_info_list:
			instance_info.options.pop("priority")
			plugins_by_name[instance_info.type] = None

		for plugin_name, none in plugins_by_name.items():
			try:
				plugin = self._plugins_repository.create(plugin_name)
				plugins_by_name[plugin_name] = plugin
				self._plugins.append(plugin)
			except tuned.plugins.exceptions.NotSupportedPluginException:
				log.info("skipping plugin '%s', not supported on your system" % plugin_name)
				continue
			except Exception as e:
				log.error("failed to initialize plugin %s" % plugin_name)
				log.exception(e)
				continue

		for instance_info in instance_info_list:
			plugin = plugins_by_name[instance_info.type]
			if plugin is None:
				continue
			log.debug("creating '%s' (%s)" % (instance_info.name, instance_info.type))
			new_instance = plugin.create_instance(instance_info.name, instance_info.devices, instance_info.devices_udev_regex, \
				instance_info.script_pre, instance_info.script_post, instance_info.options)
			plugin.assign_free_devices(new_instance)
			plugin.initialize_instance(new_instance)
			self._instances.append(new_instance)

	def destroy_all(self):
		for instance in self._instances:
			log.debug("destroying instance %s" % instance.name)
			instance.plugin.destroy_instance(instance)
		for plugin in self._plugins:
			log.debug("cleaning plugin '%s'" % plugin.name)
			plugin.cleanup()

		del self._plugins[:]
		del self._instances[:]

	def update_monitors(self):
		for monitor in self._monitors_repository.monitors:
			log.debug("updating monitor %s" % monitor)
			monitor.update()

	def start_tuning(self):
		for instance in self._instances:
			instance.apply_tuning()

	def verify_tuning(self, ignore_missing):
		ret = True
		for instance in self._instances:
			if instance.verify_tuning(ignore_missing) == False:
				ret = False
		return ret

	def update_tuning(self):
		for instance in self._instances:
			instance.update_tuning()

	# full_rollback is a helper telling plugins whether soft or full roll
	# back is needed, e.g. for bootloader plugin we need e.g grub.cfg
	# tuning to persist across reboots and restarts of the daemon, so in
	# this case the full_rollback is usually set to False,  but we also
	# need to clean it all up when Tuned is disabled or the profile is
	# changed. In this case the full_rollback is set to True. In practice
	# it means to remove all temporal or helper files, unpatch third
	# party config files, etc.
	def stop_tuning(self, full_rollback = False):
		for instance in reversed(self._instances):
			instance.unapply_tuning(full_rollback)
