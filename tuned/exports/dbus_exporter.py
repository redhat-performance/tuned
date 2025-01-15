from . import interfaces
import dbus.service
import dbus.mainloop.glib
import dbus.exceptions
import threading
import signal
import tuned.logs
import tuned.consts as consts
import traceback
import logging
from inspect import ismethod
from tuned.utils.polkit import polkit
from gi.repository import GLib
from types import FunctionType
from dbus.exceptions import DBusException
from dbus.lowlevel import ErrorMessage

try:
	# Python3 version
	# getfullargspec is not present in Python2, so when we drop P2 support
	# replace "getargspec(func)" in code with "getfullargspec(func).args"
	from inspect import getfullargspec

	def getargspec(func):
		return getfullargspec(func)
except ImportError:
	# Python2 version, drop after support stops
	from inspect import getargspec


log = tuned.logs.get()

# This is mostly copy of the code from the dbus.service module without the
# code that sends tracebacks through the D-Bus (i.e. no library tracebacks
# are exposed on the D-Bus now).
def _method_reply_error(connection, message, exception):
    name = getattr(exception, '_dbus_error_name', None)

    if name is not None:
        pass
    elif getattr(exception, '__module__', '') in ('', '__main__'):
        name = 'org.freedesktop.DBus.Python.%s' % exception.__class__.__name__
    else:
        name = 'org.freedesktop.DBus.Python.%s.%s' % (exception.__module__, exception.__class__.__name__)

    if isinstance(exception, DBusException):
        contents = exception.get_dbus_message()
    else:
        contents = ''.join(traceback.format_exception_only(exception.__class__,
            exception))
    reply = ErrorMessage(message, name, contents)

    if not message.get_no_reply():
        connection.send_message(reply)

class DBusExporter(interfaces.ExporterInterface):
	"""
	Export method calls through DBus Interface.

	We take a method to be exported and create a simple wrapper function
	to call it. This is required as we need the original function to be
	bound to the original object instance. While the wrapper will be bound
	to an object we dynamically construct.
	"""

	def __init__(self, bus_name, interface_name, object_name, namespace):
		# Monkey patching of the D-Bus library _method_reply_error() to reply
		# tracebacks via D-Bus only if in the debug mode. It doesn't seem there is a
		# more simple way how to cover all possible exceptions that could occur in
		# the D-Bus library. Just setting the exception.include_traceback to False doesn't
		# seem to help because there is only a subset of exceptions that support this flag.
		if log.getEffectiveLevel() != logging.DEBUG:
			dbus.service._method_reply_error = _method_reply_error

		dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

		self._dbus_object_cls = None
		self._dbus_object = None
		self._dbus_methods = {}
		self._signals = set()

		self._bus_name = bus_name
		self._interface_name = interface_name
		self._object_name = object_name
		self._namespace = namespace
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

	def _prepare_for_dbus(self, method, wrapper):
		source = """def {name}({args}):
					return wrapper({args})
		""".format(name=method.__name__, args=', '.join(getargspec(method.__func__).args))
		code = compile(source, '<decorator-gen-%d>' % len(self._dbus_methods), 'exec')
		# https://docs.python.org/3.9/library/inspect.html
		# co_consts - tuple of constants used in the bytecode
		# example:
		# compile("e=2\ndef f(x):\n    return x*2\n", "X", 'exec').co_consts
		# (2, <code object f at 0x7f8c60c65330, file "X", line 2>, None)
		# Because we have only one object in code (our function), we can use code.co_consts[0]
		func = FunctionType(code.co_consts[0], locals(), method.__name__)
		return func

	def _polkit_auth(self, action_name, *args):
		action_id = self._namespace + "." + action_name
		caller = args[-1]
		log.debug("checking authorization for action '%s' requested by caller '%s'" % (action_id, caller))
		ret = self._polkit.check_authorization(caller, action_id)
		args_copy = args
		if ret == 1:
			log.debug("action '%s' requested by caller '%s' was successfully authorized by polkit" % (action_id, caller))
		elif ret == 2:
			log.warning("polkit error, but action '%s' requested by caller '%s' was successfully authorized by fallback method" % (action_id, caller))
		elif ret == 0:
			log.info("action '%s' requested by caller '%s' wasn't authorized, ignoring the request" % (action_id, caller))
			args_copy = list(args[:-1]) + [""]
		elif ret == -1:
			log.warning("polkit error and action '%s' requested by caller '%s' wasn't authorized by fallback method, ignoring the request" % (action_id, caller))
			args_copy = list(args[:-1]) + [""]
		else:
			log.error("polkit error and unable to use fallback method to authorize action '%s' requested by caller '%s', ignoring the request" % (action_id, caller))
			args_copy = list(args[:-1]) + [""]
		return args_copy

	def export(self, method, in_signature, out_signature, action_name=None):
		if not ismethod(method):
			raise Exception("Only bound methods can be exported.")

		method_name = method.__name__
		if method_name in self._dbus_methods:
			raise Exception("Method with this name is already exported.")

		action_name = action_name or method_name
		def auth_wrapper(owner, *args, **kwargs):
			return method(*self._polkit_auth(action_name, *args), **kwargs)

		wrapper = self._prepare_for_dbus(method, auth_wrapper)
		wrapper = dbus.service.method(self._interface_name, in_signature, out_signature, sender_keyword = "caller")(wrapper)

		self._dbus_methods[method_name] = wrapper

	def signal(self, method, out_signature):
		if not ismethod(method):
			raise Exception("Only bound methods can be exported.")

		method_name = method.__name__
		if method_name in self._dbus_methods:
			raise Exception("Method with this name is already exported.")

		def wrapper(owner, *args, **kwargs):
			return method(*args, **kwargs)

		wrapper = self._prepare_for_dbus(method, wrapper)
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
