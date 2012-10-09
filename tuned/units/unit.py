import tuned.plugins

class Unit(object):
	"""
	Unit is the smallest tuning component. Units have to be instantiated using UnitManager.

	One unit utilizes one plugin. The tuning can be limited to certain devices with specific
	options. Multiple units can utilize one plugin, but they should not control the same
	device.
	"""

	__slots__ = ["_name", "_plugin", "_plugin_repository", "_monitor_repository"]

	def __init__(self, plugin_repository, monitor_repository, name, plugin_name, config):
		assert type(name) is str
		assert type(plugin_name) is str
		assert config is None or type(config) is dict

		self._plugin_repository = plugin_repository
		self._monitor_repository = monitor_repository
		self._name = name

		(devices, options) = self._get_plugin_params(config)
		self._plugin = self._plugin_repository.create(plugin_name, devices, options)

	@property
	def name(self):
		return self._name

	@property
	def plugin(self):
		return self._plugin

	def clean(self):
		self._plugin_repository.delete(self._plugin)
		self._plugin = None

	def _get_plugin_params(self, config):
		if config is None:
			return (None, {})

		devices = None
		assert type(config) is dict
		if "devices" in config:
			devices = config["devices"]
			if devices and len(devices) == 0:
				devices = None
			del(config["devices"])

		return (devices, config)
