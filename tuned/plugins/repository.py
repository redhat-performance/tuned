from tuned.utils.class_loader import ClassLoader
import tuned.plugins.base
import tuned.logs

log = tuned.logs.get()

__all__ = ["Repository"]

class Repository(ClassLoader):

	def __init__(self, monitor_repository, storage_factory, hardware_inventory, device_matcher, device_matcher_udev, plugin_instance_factory, global_cfg):
		super(Repository, self).__init__()
		self._plugins = set()
		self._monitor_repository = monitor_repository
		self._storage_factory = storage_factory
		self._hardware_inventory = hardware_inventory
		self._device_matcher = device_matcher
		self._device_matcher_udev = device_matcher_udev
		self._plugin_instance_factory = plugin_instance_factory
		self._global_cfg = global_cfg

	@property
	def plugins(self):
		return self._plugins

	def _set_loader_parameters(self):
		self._namespace = "tuned.plugins"
		self._prefix = "plugin_"
		self._interface = tuned.plugins.base.Plugin

	def create(self, plugin_name):
		log.debug("creating plugin %s" % plugin_name)
		plugin_cls = self.load_class(plugin_name)
		plugin_instance = plugin_cls(self._monitor_repository, self._storage_factory, self._hardware_inventory, self._device_matcher,\
			self._device_matcher_udev, self._plugin_instance_factory, self._global_cfg)
		self._plugins.add(plugin_instance)
		return plugin_instance

	def delete(self, plugin):
		assert isinstance(plugin, self._interface)
		log.debug("removing plugin %s" % plugin)
		plugin.cleanup()
		self._plugins.remove(plugin)
