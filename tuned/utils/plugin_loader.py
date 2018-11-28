import tuned.logs
import os

__all__ = ["PluginLoader"]

log = tuned.logs.get()

class PluginLoader(object):
	__slots__ = ["_namespace", "_prefix", "_interface"]

	def _set_loader_parameters(self):
		"""
		This method has to be implemented in child class and should
		set _namespace, _prefix, and _interface member attributes.
		"""
		raise NotImplementedError()

	def __init__(self):
		super(PluginLoader, self).__init__()

		self._namespace = None
		self._prefix = None
		self._interface = None
		self._set_loader_parameters()
		assert type(self._namespace) is str
		assert type(self._prefix) is str
		assert type(self._interface) is type and issubclass(self._interface, object)

	def load_plugin(self, plugin_name):
		assert type(plugin_name) is str
		module_name = "%s.%s%s" % (self._namespace, self._prefix, plugin_name)
		return self._get_class(module_name)

	def _get_class(self, module_name):
		log.debug("loading module %s" % module_name)
		module = __import__(module_name)
		path = module_name.split(".")
		path.pop(0)

		while len(path) > 0:
			module = getattr(module, path.pop(0))

		for name in module.__dict__:
			cls = getattr(module, name)
			if type(cls) is type and issubclass(cls, self._interface):
				return cls

		raise ImportError("Cannot find the plugin class.")

	def load_all_plugins(self):
		plugins_package = __import__(self._namespace)
		plugin_clss = []
		for module_name in os.listdir(plugins_package.plugins.__path__[0]):
			try:
				module_name = os.path.splitext(module_name)[0]
				if not module_name.startswith("plugin_"):
					continue
				plugin_class = self._get_class(
					"%s.%s" % (self._namespace, module_name)
					)
				if plugin_class not in plugin_clss:
					plugin_clss.append(plugin_class)
			except ImportError:
				pass
		return plugin_clss

