import tuned.logs

__all__ = ["PluginLoader"]

log = tuned.logs.get()

class PluginLoader(object):
	__slots__ = ["_namespace", "_prefix", "_interface"]

	def __init__(self, namespace, prefix, interface):
		super(self.__class__, self).__init__()

		assert type(namespace) is str
		assert type(prefix) is str
		assert type(interface) is type and issubclass(interface, object)

		self._namespace = namespace
		self._prefix = prefix
		self._interface = interface

	@property
	def namespace(self):
		return self._namespace

	@property
	def prefix(self):
		return self._prefix

	@property
	def interface(self):
		return self._interface

	def load(self, plugin_name):
		assert type(plugin_name) is str

		module_name = "%s.%s%s" % (self._namespace, self._prefix, plugin_name)
		module = self._get_module(module_name)
		return module

	def _get_module(self, module_name):
		log.debug("loading module %s" % module_name)
		module = __import__(module_name)
		path = module_name.split(".")
		path.pop(0)

		while len(path) > 0:
			module = getattr(module, path.pop(0))

		for name in module.__dict__:
			obj = getattr(module, name)
			if type(obj) is type and issubclass(obj, self._interface):
				return obj

		raise ImportError("Cannot find the plugin class.")

