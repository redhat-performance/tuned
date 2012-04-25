import tuned.patterns
import tuned.logs
import tuned.utils
import tuned.plugins
import tuned.plugins.exception

log = tuned.logs.get()

class PluginRepository(tuned.patterns.Singleton):
	def __init__(self):
		super(self.__class__, self).__init__()
		self._loader = tuned.utils.PluginLoader("tuned.plugins", "plugin_", tuned.plugins.Plugin)
		self._plugins = set()

	def create(self, plugin_name, devices, options):
		log.debug("creating plugin %s" % plugin_name)
		try:
			plugin_cls = self._loader.load(plugin_name)
			plugin_instance = plugin_cls(devices, options)
			self._plugins.add(plugin_instance)
			return plugin_instance
		except Exception as exception:
			plugin_exception = tuned.plugins.exception.LoadPluginException(plugin_name, exception)
			raise plugin_exception

	def tunable_devices(self, plugin_name):
		try:
			plugin_cls = self._loader.load(plugin_name)
			return plugin_cls.tunable_devices()
		except Exception as exception:
			plugin_exception = tuned.plugins.exception.LoadPluginException(plugin_name, exception)
			raise plugin_exception

	def is_supported(self, plugin_name):
		try:
			plugin_cls = self._loader.load(plugin_name)
			return plugin_cls.is_supported()
		except Exception as exception:
			plugin_exception = tuned.plugins.exception.LoadPluginException(plugin_name, exception)
			raise plugin_exception

	def delete(self, plugin):
		assert isinstance(plugin, self._loader.interface)
		log.debug("removing plugin %s" % plugin)
		plugin.cleanup()
		self._plugins.remove(plugin)

	def update(self):
		for plugin in self._plugins:
			log.debug("updating %s" % plugin)
			plugin.update_tuning()
