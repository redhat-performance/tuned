import tuned.exceptions
import tuned.logs
import tuned.patterns
import tuned.units.unit

log = tuned.logs.get()

__all__ = ["Manager"]

class Manager(object):
	"""
	Manager instantiates Unit objects, and keeps track of them.
	"""

	__slots__ = ["_units", "_plugins_repository", "_monitors_repository"]

	def __init__(self, plugins_repository, monitors_repository):
		super(self.__class__, self).__init__()
		self._units = set()
		self._plugins_repository = plugins_repository
		self._monitors_repository = monitors_repository

	@property
	def units(self):
		return self._units.copy()

	@property
	def plugins_repository(self):
		return self._plugins_repository

	@property
	def monitors_repository(self):
		return self._monitors_repository

	def create(self, name, plugin_name, config):
		log.info("creating unit '%s'" % name)
		try:
			new_unit = tuned.units.unit.Unit(self._plugins_repository, self._monitors_repository, name, plugin_name, config)
			self._units.add(new_unit)
			return new_unit
		except tuned.exceptions.TunedException as e:
			e.log()
			log.error("unable to create unit '%s'" % name)

	def delete(self, unit):
		assert type(unit) is tuned.units.unit.Unit
		unit.clean()
		self._units.delete(unit)

	def delete_all(self):
		for unit in self._units:
			unit.clean()
		self._units.clear()
