#
# Author: Jan Vcelak <jvcelak@redhat.com>
#

from __future__ import absolute_import

import exports.interfaces
import decorator
import dbus.service
import dbus.mainloop.glib
import gobject
import inspect

class DBusExporter(exports.interfaces.IExporter):
	"""
	Export method calls through DBus Interface.

	We take a method to be exported and create a simple wrapper function
	to call it. This is required as we need the original function to be
	bound to the original object instance. While the wrapper will be bound
	to an object we dynamically construct.
	"""

	def __init__(self, bus_name, interface_name, object_name):
		self._dbus_object_cls = None
		self._dbus_object = None
		self._dbus_methods = {}

		self._bus_name = bus_name
		self._interface_name = interface_name
		self._object_name = object_name

	@property
	def bus_name(self):
		return self._bus_name

	@property
	def interface_name(self):
		return self._interface_name

	@property
	def object_name(self):
		return self._object_name

	def export(self, method, in_signature, out_signature):
		if not inspect.ismethod(method):
			raise Exception("Only bound methods can be exported.")

		method_name = method.__name__
		if method_name in self._dbus_methods:
			raise Exception("Method with this name is already exported.")

		def wrapper(wrapped, owner, *args, **kwargs):
			return method(*args, **kwargs)

		wrapper = decorator.decorator(wrapper, method.im_func)
		wrapper = dbus.service.method(self._interface_name, in_signature, out_signature)(wrapper)

		self._dbus_methods[method_name] = wrapper

	def _construct_dbus_object_class(self):
		if self._dbus_object_cls is not None:
			raise Exception("The exporter class was already build.")

		unique_name = "DBusExporter_%d" % id(self)
		cls = type(unique_name, (dbus.service.Object,), self._dbus_methods)

		self._dbus_object_cls = cls

	def run(self):
		dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

		bus = dbus.SessionBus()
		bus_name = dbus.service.BusName(self._bus_name, bus)

		self._construct_dbus_object_class()
		dbus_object = self._dbus_object_cls(bus, self._object_name, bus_name)

		loop = gobject.MainLoop()
		loop.run()
