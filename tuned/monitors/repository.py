import tuned.patterns
import tuned.logs
import tuned.utils

log = tuned.logs.get()

class MonitorRepository(tuned.patterns.Singleton):
	def __init__(self):
		super(self.__class__, self).__init__()
		self._loader = tuned.utils.PluginLoader("tuned.monitors", "monitor_", tuned.monitors.Monitor)
		self._monitors = set()

	def create(self, plugin_name, devices):
		log.debug("creating monitor %s" % plugin_name)
		# TODO: exception handling
		monitor_cls = self._loader.load(plugin_name)

		for monitor in self._monitors:
			if (isinstance(monitor, monitor_cls) and 
				(monitor.devices == devices or devices == None)):
				return monitor

		monitor_instance = monitor_cls(devices)
		self._monitors.add(monitor_instance)
		return monitor_instance

	def delete(self, monitor):
		assert isinstance(monitor, self._loader.interface)
		monitor.cleanup()
		self._monitors.remove(monitor)

	def update(self):
		for monitor in self._monitors:
			log.debug("updating %s" % monitor)
			monitor.update()
