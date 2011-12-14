import tuned.plugins.interface
import tuned.monitors

class TestPlugin(tuned.plugins.interface.PluginInterface):
	def __init__(self, options = None):
		"""
		"""
		super(self.__class__, self).__init__(options)

		self._monitors = [
			tuned.monitors.get_repository().create("load"),
			tuned.monitors.get_repository().create("disk")
		]

	def cleanup(self):
		for monitor in self._monitors:
			tuned.monitors.get_repository().delete(monitor)

	def update_tuning(self):
		pass
