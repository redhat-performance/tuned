from . import interfaces
import decorator
import dbus.service
import dbus.mainloop.glib
import dbus.exceptions
import inspect
import threading
import signal
import tuned.logs
import tuned.consts as consts
from tuned.utils.polkit import polkit
from gi.repository import GLib

log = tuned.logs.get()

class DBusExporter(interfaces.ExporterInterface):
	"""
	Export method calls through DBus Interface.

	We take a method to be exported and create a simple wrapper function
	to call it. This is required as we need the original function to be
	bound to the original object instance. While the wrapper will be bound
	to an object we dynamically construct.
	"""

	def __init__(self, bus_name, interface_name, object_name):
		dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

		self._dbus_object_cls = None
		self._dbus_object = None
		self._dbus_methods = {}
		self._signals = set()

		self._bus_name = bus_name
		self._interface_name = interface_name
		self._object_name = object_name
		self._thread = None
		self._bus_object = None
		self._polkit = polkit()

		# dirty hack that fixes KeyboardInterrupt handling
		# the hack is needed because PyGObject / GTK+-3 developers are morons
		signal_handler = signal.getsignal(signal.SIGINT)
		self._main_loop = GLib.MainLoop()
		signal.signal(signal.SIGINT, signal_handler)

	@property
	def bus_name(self):
		return self._bus_name

	@property
	def interface_name(self):
		return self._interface_name

	@property
	def object_name(self):
		return self._object_name

	def running(self):
		return self._thread is not None

	def export(self, method, in_signature, out_signature):
		if not inspect.ismethod(method):
			raise Exception("Only bound methods can be exported.")

		method_name = method.__name__
		if method_name in self._dbus_methods:
			raise Exception("Method with this name is already exported.")

		def wrapper(wrapped, owner, *args, **kwargs):
			action_id = consts.NAMESPACE + "." + method.__name__
			caller = args[-1]
			log.debug("checking authorization for for action '%s' requested by caller '%s'" % (action_id, caller))
			ret = self._polkit.check_authorization(caller, action_id)
			if ret == 1:
					log.debug("action '%s' requested by caller '%s' was successfully authorized by polkit" % (action_id, caller))
			elif ret == 2:
					log.warn("polkit error, but action '%s' requested by caller '%s' was successfully authorized by fallback method" % (action_id, caller))
			elif ret == 0:
					log.info("action '%s' requested by caller '%s' wasn't authorized, ignoring the request" % (action_id, caller))
					args[-1] = ""
			elif ret == -1:
				log.warn("polkit error and action '%s' requested by caller '%s' wasn't authorized by fallback method, ignoring the request" % (action_id, caller))
				args[-1] = ""
			else:
				log.error("polkit error and unable to use fallback method to authorize action '%s' requested by caller '%s', ignoring the request" % (action_id, caller))
				args[-1] = ""
			return method(*args, **kwargs)

		wrapper = decorator.decorator(wrapper, method.__func__)
		wrapper = dbus.service.method(self._interface_name, in_signature, out_signature, sender_keyword = "caller")(wrapper)

		self._dbus_methods[method_name] = wrapper

	def signal(self, method, out_signature):
		if not inspect.ismethod(method):
			raise Exception("Only bound methods can be exported.")

		method_name = method.__name__
		if method_name in self._dbus_methods:
			raise Exception("Method with this name is already exported.")

		def wrapper(wrapped, owner, *args, **kwargs):
			return method(*args, **kwargs)

		wrapper = decorator.decorator(wrapper, method.__func__)
		wrapper = dbus.service.signal(self._interface_name, out_signature)(wrapper)

		self._dbus_methods[method_name] = wrapper
		self._signals.add(method_name)

	def send_signal(self, signal, *args, **kwargs):
		err = False
		if not signal in self._signals or self._bus_object is None:
			err = True
		try:
			method = getattr(self._bus_object, signal)
		except AttributeError:
			err = True
		if err:
			raise Exception("Signal '%s' doesn't exist." % signal)
		else:
			method(*args, **kwargs)

	def _construct_dbus_object_class(self):
		if self._dbus_object_cls is not None:
			raise Exception("The exporter class was already build.")

		unique_name = "DBusExporter_%d" % id(self)
		cls = type(unique_name, (dbus.service.Object,), self._dbus_methods)

		self._dbus_object_cls = cls

	def start(self):
		if self.running():
			return
		if self._dbus_object_cls is None:
			self._construct_dbus_object_class()

		self.stop()
		bus = dbus.SystemBus()
		bus_name = dbus.service.BusName(self._bus_name, bus)
		self._bus_object = self._dbus_object_cls(bus, self._object_name, bus_name)
		self._thread = threading.Thread(target=self._thread_code)
		self._thread.start()

	def stop(self):
		if self._thread is not None and self._thread.is_alive():
			self._main_loop.quit()
			self._thread.join()
			self._thread = None

	def _thread_code(self):
		self._main_loop.run()
		del self._bus_object
		self._bus_object = None
