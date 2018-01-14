import tuned.logs
import tuned.monitors
from tuned.utils.plugin_loader import PluginLoader

log = tuned.logs.get()

__all__ = ["Repository"]

class Repository(PluginLoader):

	def __init__(self):
		super(Repository, self).__init__()
		self._monitors = set()

	@property
	def monitors(self):
		return self._monitors

	def _set_loader_parameters(self):
		self._namespace = "tuned.monitors"
		self._prefix = "monitor_"
		self._interface = tuned.monitors.Monitor

	def create(self, plugin_name, devices):
		log.debug("creating monitor %s" % plugin_name)
		monitor_cls = self.load_plugin(plugin_name)
		monitor_instance = monitor_cls(devices)
		self._monitors.add(monitor_instance)
		return monitor_instance

	def delete(self, monitor):
		assert isinstance(monitor, self._interface)
		monitor.cleanup()
		self._monitors.remove(monitor)
