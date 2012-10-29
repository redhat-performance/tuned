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

	__slots__ = ["_units", "_plugins_repository", "_monitors_repository", "_unit_factory", "_device_matcher"]

	def __init__(self, plugins_repository, monitors_repository, unit_factory, device_matcher):
		super(self.__class__, self).__init__()
		self._units = set()
		self._monitors_repository = monitors_repository
		self._plugins_repository = plugins_repository
		self._unit_factory = unit_factory
		self._device_matcher = device_matcher

	@property
	def units(self):
		return self._units

	@property
	def plugins_repository(self):
		return self._plugins_repository

	@property
	def monitors_repository(self):
		return self._monitors_repository

	def create(self, units):
		# reverse order, newer units have priority to claim a device
		for unit_info in reversed(units):
			if not unit_info.enabled:
				log.debug("skipping disabled unit '%s'" % unit_info.name)
				continue

			if not self._plugins_repository.is_supported(unit_info.type):
				log.info("skipping unit '%s', plugin not supported on your system" % unit_info.type)
				continue

			devices = self._possible_devices(unit_info)
			if devices is None:
				continue

			log.info("creating unit '%s' (devices: %s)" % (unit_info.name, ", ".join(devices)))
			try:
				self._create_unit(unit_info, devices)
			except tuned.exceptions.TunedException as e:
				log.error("unable to create unit '%s' (trace follows)" % unit_info.name)
				e.log()
			except Exception as E:
				log.error("unable to create unit '%s' (%s)" % (unit_info.name, str(e)))

	def _possible_devices(self, unit_info):
		tunable_devices = self._plugins_repository.tunable_devices(unit_info.type)
		if not tunable_devices:
			log.info("skipping unit '%s', no devices available" % unit_info.name)
			return None

		available_devices = [dev for dev in tunable_devices if dev not in self._seized_devices(unit_info.type)]
		if not available_devices:
			log.info("skipping unit '%s', all devices are already claimed by another unit" % unit_info.name)
			return None

		devices = self._device_matcher.match_list(unit_info.devices, available_devices)
		if not devices:
			log.info("skipping unit '%s', no matching devices available" % unit_info.name)
			return None

		return devices

	def _seized_devices(self, type):
		devices = []
		for unit in self._units:
			if unit.type == type:
				devices.extend(unit.devices)
		return set(devices)

	def _create_unit(self, unit_info, devices):
		plugin = self._plugins_repository.create(unit_info.type, devices, unit_info.options)
		unit = self._unit_factory.create(unit_info.name, unit_info.type, plugin)
		self._units.add(unit)

	def delete(self, unit):
		self._plugins_repository.delete(unit.plugin)
		self._units.delete(unit)

	def delete_all(self):
		for unit in self._units:
			self._plugins_repository.delete(unit.plugin)
		self._units.clear()
