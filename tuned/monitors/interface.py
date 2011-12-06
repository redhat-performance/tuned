class MonitorInterface(object):
	"""

	Following methods require reimlementation:
	  - _init_available_devices(cls)
	  - update(cls)

	"""

	# class properties

	_class_initialized = False
	_instances = set()
	_available_devices = set()
	_updating_devices = set()
	_load = {}

	@classmethod
	def _init_class(cls):
		cls._init_available_devices()
		assert(type(cls._available_devices) is set)
		cls._class_initialized = True

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

	# instance properties

	def __init__(self, devices = None):
		if self._class_initialized is False:
			self._init_class()
			assert(self._class_initialized)

		if devices is not None:
			self.devices = devices
		else:
			self.devices = self.get_available_devices()

		self.update()
		self._register_instance(self)

	def __del__(self):
		self.cleanup()

	def cleanup(self):
		self.deregister_instance(self)

	@property
	def devices(self):
		return self._devices

	@devices.setter
	def devices(self, value):
		new_devices = self._available_devices & set(value)
		self._devices = new_devices

		new_updating = set()
		for instance in self._instances:
			new_updating |= instance.devices
		self._updating_devices.clear()
		self._updating_devices.update(new_updating)

	def add_device(self, device):
		if device in self._available_devices:
			self._devices.add(device)
			self._updating_devices.add(device)

	def remove_device(self, device):
		if device in self._devices:
			self._devices.remove(device)
			self._updating_devices.remove(device)

	def get_load(self):
		return dict(filter(lambda (dev, load): dev in self._devices, self._load.items()))
