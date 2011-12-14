import tuned.plugins

class Unit(object):
	__slots__ = ["_name", "_plugin", "_devices", "_options"]

	def __init__(self, name, plugin_name, devices, options = None):
		assert type(name) is str
		assert type(plugin_name) is str
		assert type(devices) is list
		assert options is None or type(options) is list

		self._name = name
		self._devices = devices
		self._options = options
		self._plugin = tuned.plugins.get_repository().create(plugin_name)

	@property
	def name(self):
		return self._name

	@property
	def devices(self):
		return self._devices[:]

	def clean(self):
		tuned.plugins.get_repository().delete(self._plugin)
		self._plugin = None
