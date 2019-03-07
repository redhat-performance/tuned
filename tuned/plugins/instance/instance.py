class Instance(object):
	"""
	"""

	def __init__(self, plugin, name, devices_expression, devices_udev_regex, script_pre, script_post, options):
		self._plugin = plugin
		self._name = name
		self._devices_expression = devices_expression
		self._devices_udev_regex = devices_udev_regex
		self._script_pre = script_pre
		self._script_post = script_post
		self._options = options

		self._active = True
		self._has_static_tuning = False
		self._has_dynamic_tuning = False
		self._assigned_devices = set()
		self._processed_devices = set()

	# properties

	@property
	def plugin(self):
		return self._plugin

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
	def assigned_devices(self):
		return self._assigned_devices

	@property
	def processed_devices(self):
		return self._processed_devices

	@property
	def devices_udev_regex(self):
		return self._devices_udev_regex

	@property
	def script_pre(self):
		return self._script_pre

	@property
	def script_post(self):
		return self._script_post

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

	def verify_tuning(self, ignore_missing):
		return self._plugin.instance_verify_tuning(self, ignore_missing)

	def update_tuning(self):
		self._plugin.instance_update_tuning(self)

	def unapply_tuning(self, full_rollback = False):
		self._plugin.instance_unapply_tuning(self, full_rollback)

	def destroy(self):
		self.unapply_tuning()
		self._plugin.destroy_instance(self)
