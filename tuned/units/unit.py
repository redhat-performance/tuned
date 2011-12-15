import tuned.plugins

class Unit(object):
	"""
	Unit is the smallest tuning component. Units have to be insantiated using UnitManager.

	One unit utilizes one plugin. The tuning can be limited to certain devices with specific
	options. Multiple units can utilize one plugin, but they should not control the same
	device.
	"""

	__slots__ = ["_name", "_plugin"]

	def __init__(self, name, plugin_name, devices = None, options = None):
		assert type(name) is str
		assert type(plugin_name) is str
		assert devices is None or type(devices) is list
		assert options is None or type(options) is dict

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
