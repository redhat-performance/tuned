import base
import exceptions

import tuned.logs
import tuned.utils

log = tuned.logs.get()

__all__ = ["Repository"]

class Repository(object):

	__slots__ = ["_loader", "_plugins", "_storage_factory"]

	def __init__(self, storage_factory):
		super(self.__class__, self).__init__()
		self._loader = tuned.utils.PluginLoader("tuned.plugins", "plugin_", base.Plugin)
		self._plugins = set()
		self._storage_factory = storage_factory

	def create(self, monitor_repository, plugin_name, devices, options):
		log.debug("creating plugin %s" % plugin_name)
		try:
			plugin_cls = self._loader.load(plugin_name)
			plugin_instance = plugin_cls(monitor_repository, self._storage_factory, devices, options)
			self._plugins.add(plugin_instance)
			return plugin_instance
		except Exception as exception:
			plugin_exception = exceptions.LoadPluginException(plugin_name, exception)
			raise plugin_exception

	def tunable_devices(self, plugin_name):
		try:
			plugin_cls = self._loader.load(plugin_name)
			return plugin_cls.tunable_devices()
		except Exception as e:
			plugin_exception = exceptions.LoadPluginException(plugin_name, e)
			raise plugin_exception

	def is_supported(self, plugin_name):
		try:
			plugin_cls = self._loader.load(plugin_name)
			return plugin_cls.is_supported()
		except Exception as e:
			plugin_exception = exceptions.LoadPluginException(plugin_name, e)
			raise plugin_exception

	def do_static_tuning(self):
		for plugin in self._plugins:
			if not plugin.static_tuning:
				continue
			
			# TODO: plugin to str conversion, not ideal now
			log.debug("running static tuning for plugin '%s'" % plugin)
			plugin.cleanup_commands()
			plugin.execute_commands()

	def delete(self, plugin):
		assert isinstance(plugin, self._loader.interface)
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
