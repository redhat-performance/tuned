import tuned.plugins

class Unit(object):
	"""
	Unit is the smallest tuning component. Units have to be instantiated using UnitManager.

	One unit utilizes one plugin. The tuning can be limited to certain devices with specific
	options. Multiple units can utilize one plugin, but they should not control the same
	device.
	"""

	__slots__ = ["_name", "_type", "_plugin"]

	def __init__(self, name, type, plugin):
		self._name = name
		self._type = type
		self._plugin = plugin

	@property
	def name(self):
		return self._name

	@property
	def type(self):
		return self._type

	@property
	def devices(self):
		return self._plugin.devices

	@property
	def plugin(self):
		return self._plugin
