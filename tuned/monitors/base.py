import tuned.logs
log = tuned.logs.get()

__all__ = ["Monitor"]

class Monitor(object):
	"""
	Base class for all monitors.

	Monitors provide data about the running system to Plugin objects, which use the data
	to tune system parameters.

	Following methods require reimplementation:
	  - _init_available_devices(cls)
	  - update(cls)
	"""

	# class properties

	@classmethod
	def _init_class(cls):
		cls._class_initialized = False
		cls._instances = set()
		cls._available_devices = set()
		cls._updating_devices = set()
		cls._load = {}

		cls._init_available_devices()
		assert isinstance(cls._available_devices, set)
		cls._class_initialized = True
		log.debug("available devices: %s" % ", ".join(cls._available_devices))

	@classmethod
	def _init_available_devices(cls):
		raise NotImplementedError()

	@classmethod
	def get_available_devices(cls):
		return cls._available_devices

	@classmethod
	def update(cls):
		raise NotImplementedError()

	@classmethod
	def _register_instance(cls, instance):
		cls._instances.add(instance)

	@classmethod
	def _deregister_instance(cls, instance):
		cls._instances.remove(instance)

	@classmethod
	def _refresh_updating_devices(cls):
		new_updating = set()
		for instance in cls._instances:
			new_updating |= instance.devices
		cls._updating_devices.clear()
		cls._updating_devices.update(new_updating)

	@classmethod
	def instances(cls):
		return cls._instances

	# instance properties

	def __init__(self, devices = None):
		if not hasattr(self, "_class_initialized"):
			self._init_class()
			assert hasattr(self, "_class_initialized")

		self._register_instance(self)

		if devices is not None:
			self.devices = devices
		else:
			self.devices = self.get_available_devices()

		self.update()

	def __del__(self):
		try:
			self.cleanup()
		except:
			pass

	def cleanup(self):
		self._deregister_instance(self)
		self._refresh_updating_devices()

	@property
	def devices(self):
		return self._devices

	@devices.setter
	def devices(self, value):
		new_devices = self._available_devices & set(value)
		self._devices = new_devices
		self._refresh_updating_devices()

	def add_device(self, device):
		assert isinstance(device, str)
		if device in self._available_devices:
			self._devices.add(device)
			self._updating_devices.add(device)

	def remove_device(self, device):
		assert isinstance(device, str)
		if device in self._devices:
			self._devices.remove(device)
			self._updating_devices.remove(device)

	def get_load(self):
		return dict([dev_load for dev_load in list(self._load.items()) if dev_load[0] in self._devices])

	def get_device_load(self, device):
		return self._load.get(device, None)
