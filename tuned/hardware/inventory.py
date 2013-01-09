import pyudev

class Inventory(object):
	"""
	Inventory object can handle information about available hardware devices. It also informs the plugins
	about related hardware events.
	"""

	def __init__(self, udev_context=None):
		if udev_context is not None:
			self._udev_context = udev_context
		else:
			self._udev_context = pyudev.Context()

	def get_devices(self, subsystem):
		return self._udev_context.list_devices(subsystem=subsystem)

	def subscribe(self, plugin, subsystem, callback):
		pass

	def unsubscribe(self, plugin, subsystem=None):
		pass
