import tuned.exceptions
import tuned.logs
import tuned.plugins.exceptions

log = tuned.logs.get()

__all__ = ["Manager"]

class Manager(object):
	"""
	Manager creates plugin instances and keeps a track of them.
	"""

	def __init__(self, plugins_repository, monitors_repository):
		super(self.__class__, self).__init__()
		self._plugins_repository = plugins_repository
		self._monitors_repository = monitors_repository
		self._instances = []
		self._plugins = []

	@property
	def plugins(self):
		return self._plugins

	@property
	def instances(self):
		return self._instances

	def create(self, instances_config):

		# group instances by plugin

		instances_by_plugin = {}
		for instance_name, instance_info in instances_config.items():
			if not instance_info.enabled:
				log.debug("skipping disabled instance '%s'" % instance_name)
				continue
			instances_by_plugin.setdefault(instance_info.type, [])
			instances_by_plugin[instance_info.type].append(instance_info)

		# create all plugin instances at once

		for plugin_name, instances_info in instances_by_plugin.items():
			try:
				plugin = self._plugins_repository.create(plugin_name)
				self._plugins.append(plugin)
			except tuned.plugins.exceptions.NotSupportedPluginException:
				log.info("skipping plugin '%s', not supported on your system" % plugin_name)
				continue
			except Exception as e:
				log.error("failed to initialize plugin %s" % plugin_name)
				log.exception(e)
				continue

			created_instances = []
			for instance_info in instances_info:
				log.debug("creating '%s' (%s)" % (instance_info.name, instance_info.type))
				new_instance = plugin.create_instance(instance_info.name, instance_info.devices, instance_info.options)
				created_instances.append(new_instance)

			plugin.assign_free_devices()
			plugin.initialize_instances()

			self._instances.extend(created_instances)

	def destroy_all(self):
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

	def verify_tuning(self):
		ret = True
		for instance in self._instances:
			if instance.verify_tuning() == False:
				ret = False
		return ret

	def update_tuning(self):
		for instance in self._instances:
			instance.update_tuning()

	# profile_switch is helper telling plugins whether the stop is due to profile switch
	def stop_tuning(self, profile_switch = False):
		for instance in self._instances:
			instance.unapply_tuning(profile_switch)
