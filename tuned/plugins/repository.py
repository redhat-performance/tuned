from tuned.utils.plugin_loader import PluginLoader
import tuned.plugins.base
import tuned.logs

log = tuned.logs.get()

__all__ = ["Repository"]

class Repository(PluginLoader):

	def __init__(self, storage_factory, monitor_repository):
		super(self.__class__, self).__init__()
		self._plugins = set()
		self._storage_factory = storage_factory
		self._monitor_repository = monitor_repository

	def _set_loader_parameters(self):
		self._namespace = "tuned.plugins"
		self._prefix = "plugin_"
		self._interface = tuned.plugins.base.Plugin

	def create(self, plugin_name, devices, options):
		log.debug("creating plugin %s" % plugin_name)
		plugin_cls = self.load_plugin(plugin_name)
		plugin_instance = plugin_cls(self._monitor_repository, self._storage_factory, devices, options)
		self._plugins.add(plugin_instance)
		return plugin_instance

	def tunable_devices(self, plugin_name):
		plugin_cls = self.load_plugin(plugin_name)
		return plugin_cls.tunable_devices()

	def is_supported(self, plugin_name):
		plugin_cls = self.load_plugin(plugin_name)
		return plugin_cls.is_supported()

	def do_static_tuning(self):
		for plugin in self._plugins:
			# TODO: plugin to str conversion, not ideal now
			log.debug("running static tuning for plugin '%s'" % plugin)
			plugin.cleanup_commands()
			plugin.execute_commands()

	def delete(self, plugin):
		assert isinstance(plugin, self._interface)
		log.debug("removing plugin %s" % plugin)
		plugin.cleanup_commands()
		plugin.cleanup()
		self._plugins.remove(plugin)

	def update(self):
		for plugin in self._plugins:
			if not plugin.dynamic_tuning:
				continue
			log.debug("updating %s" % plugin)
			plugin.update_tuning()
