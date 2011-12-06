import tuned.patterns
import tuned.logs
import tuned.monitors.interface

log = tuned.logs.get()

class MonitorRepository(tuned.patterns.Singleton):
	def __init__(self):
		super(self.__class__, self).__init__()
		self._monitors = set()

	def _load_plugin(self, plugin_name):
		module_name = "monitor_%s" % plugin_name
		module = __import__("tuned.monitors.%s" % module_name)
		module = getattr(module.monitors, module_name)

		for name in module.__dict__:
			print name
			item = getattr(module, name)
			if type(item) is type and issubclass(item, tuned.monitors.interface.MonitorInterface):
				return item

		raise ImportError("No monitor plugin in the module")

	def create(self, plugin_name):
		log.debug("creating monitor %s" % plugin_name)
		plugin_cls = self._load_plugin(plugin_name)
		plugin_instance = plugin_cls()
		self._monitors.add(plugin_instance)
		return plugin_instance

	def delete(self, monitor):
		assert(type(monitor) is tuned.monitor.interface.MonitorInterface)
		monitor.cleanup()
		self._monitors.remove(monitor)

	def update(self):
		for monitor in self._monitors:
			log.debug("updating %s")
			monitor.update()
