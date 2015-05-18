class Instance(object):
	"""
	"""

	def __init__(self, plugin, name, devices_expression, options):
		self._plugin = plugin
		self._name = name
		self._devices_expression = devices_expression
		self._options = options

		self._active = True
		self._has_static_tuning = False
		self._has_dynamic_tuning = False
		self._devices = set()

	# properties

	@property
	def name(self):
		return self._name

	@property
	def active(self):
		"""The instance performs some tuning (otherwise it is suspended)."""
		return self._active

	@active.setter
	def active(self, value):
		self._active = value

	@property
	def devices_expression(self):
		return self._devices_expression

	@property
	def devices(self):
		return self._devices

	@property
	def options(self):
		return self._options

	@property
	def has_static_tuning(self):
		return self._has_static_tuning

	@property
	def has_dynamic_tuning(self):
		return self._has_dynamic_tuning

	# methods

	def apply_tuning(self):
		self._plugin.instance_apply_tuning(self)

	def verify_tuning(self):
		return self._plugin.instance_verify_tuning(self)

	def update_tuning(self):
		self._plugin.instance_update_tuning(self)

	def unapply_tuning(self, profile_switch = False):
		self._plugin.instance_unapply_tuning(self, profile_switch)

	def destroy(self):
		self.unapply_tuning()
		self._plugin.destroy_instance(self)
