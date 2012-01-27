import tuned.plugins

class Unit(object):
	"""
	Unit is the smallest tuning component. Units have to be instantiated using UnitManager.

	One unit utilizes one plugin. The tuning can be limited to certain devices with specific
	options. Multiple units can utilize one plugin, but they should not control the same
	device.
	"""

	__slots__ = ["_name", "_plugin"]

	def __init__(self, name, plugin_name, config):
		assert type(name) is str
		assert type(plugin_name) is str
		assert config is None or type(config) is dict

		(devices, options) = self._get_plugin_params(config)

		self._name = name
		self._plugin = tuned.plugins.get_repository().create(plugin_name, devices, options)

	@property
	def name(self):
		return self._name

	@property
	def plugin(self):
		return self._plugin

	def clean(self):
		tuned.plugins.get_repository().delete(self._plugin)
		self._plugin = None

	def _get_plugin_params(self, config):
		if config is None:
			return (None, {})

		devices = None
		assert type(config) is dict
		if "devices" in config:
			devices = config[devices].strip().split()
			if len(devices) == 0:
				devices = None
			del(config["devices"])

		return (devices, config)
