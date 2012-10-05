class Unit(object):
	"""
	Unit description.
	"""

	__slots__ = [ "_name", "_plugin", "_options" ]

	def __init__(self, name, plugin, options):
		self._name = name
		self._plugin = plugin
		self._options = options

	@property
	def name(self):
		return self._name

	@property
	def plugin(self):
		return self._plugin

	@property
	def options(self):
		return self._options
