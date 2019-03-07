import pyudev
import tuned.logs
from tuned import consts

__all__ = ["Inventory"]

log = tuned.logs.get()

class Inventory(object):
	"""
	Inventory object can handle information about available hardware devices. It also informs the plugins
	about related hardware events.
	"""

	def __init__(self, udev_context=None, udev_monitor_cls=None, monitor_observer_factory=None, buffer_size=None, set_receive_buffer_size=True):
		if udev_context is not None:
			self._udev_context = udev_context
		else:
			self._udev_context = pyudev.Context()

		if udev_monitor_cls is None:
			udev_monitor_cls = pyudev.Monitor
		self._udev_monitor = udev_monitor_cls.from_netlink(self._udev_context)
		if buffer_size is None:
			buffer_size = consts.CFG_DEF_UDEV_BUFFER_SIZE

		if (set_receive_buffer_size):
			self._udev_monitor.set_receive_buffer_size(buffer_size)

		if monitor_observer_factory is None:
			monitor_observer_factory = _MonitorObserverFactory()
		self._monitor_observer_factory = monitor_observer_factory
		self._monitor_observer = None

		self._subscriptions = {}

	def get_device(self, subsystem, sys_name):
		"""Get a pyudev.Device object for the sys_name (e.g. 'sda')."""
		try:
			return pyudev.Devices.from_name(self._udev_context, subsystem, sys_name)
		# workaround for pyudev < 0.18
		except AttributeError:
			return pyudev.Device.from_name(self._udev_context, subsystem, sys_name)

	def get_devices(self, subsystem):
		"""Get list of devices on a given subsystem."""
		return self._udev_context.list_devices(subsystem=subsystem)

	def _handle_udev_event(self, event, device):
		if not device.subsystem in self._subscriptions:
			return

		for (plugin, callback) in self._subscriptions[device.subsystem]:
			try:
				callback(event, device)
			except Exception as e:
				log.error("Exception occured in event handler of '%s'." % plugin)
				log.exception(e)

	def subscribe(self, plugin, subsystem, callback):
		"""Register handler of device events on a given subsystem."""
		log.debug("adding handler: %s (%s)" % (subsystem, plugin))
		callback_data = (plugin, callback)
		if subsystem in self._subscriptions:
			self._subscriptions[subsystem].append(callback_data)
		else:
			self._subscriptions[subsystem] = [callback_data, ]
			self._udev_monitor.filter_by(subsystem)
			# After start(), HW events begin to get queued up
			self._udev_monitor.start()

	def start_processing_events(self):
		if self._monitor_observer is None:
			log.debug("starting monitor observer")
			self._monitor_observer = self._monitor_observer_factory.create(self._udev_monitor, self._handle_udev_event)
			self._monitor_observer.start()

	def stop_processing_events(self):
		if self._monitor_observer is not None:
			log.debug("stopping monitor observer")
			self._monitor_observer.stop()
			self._monitor_observer = None

	def _unsubscribe_subsystem(self, plugin, subsystem):
		for callback_data in self._subscriptions[subsystem]:
			(_plugin, callback) = callback_data
			if plugin == _plugin:
				log.debug("removing handler: %s (%s)" % (subsystem, plugin))
				self._subscriptions[subsystem].remove(callback_data)

	def unsubscribe(self, plugin, subsystem=None):
		"""Unregister handler registered with subscribe method."""
		empty_subsystems = []
		for _subsystem in self._subscriptions:
			if subsystem is None or _subsystem == subsystem:
				self._unsubscribe_subsystem(plugin, _subsystem)
				if len(self._subscriptions[_subsystem]) == 0:
					empty_subsystems.append(_subsystem)

		for _subsystem in empty_subsystems:
			del self._subscriptions[_subsystem]

class _MonitorObserverFactory(object):
	def create(self, *args, **kwargs):
		return pyudev.MonitorObserver(*args, **kwargs)
