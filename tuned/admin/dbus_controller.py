import threading
import dbus
import dbus.exceptions
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
from exceptions import TunedAdminDBusException

__all__ = ["DBusController"]

class DBusController(object):
	def __init__(self, bus_name, interface_name, object_name, debug = False):
		self._bus_name = bus_name
		self._interface_name = interface_name
		self._object_name = object_name
		self._proxy = None
		self._debug = debug
		self._main_loop = None
		self._thread = None

	def _init_proxy(self):
		try:
			if self._proxy is None:
				DBusGMainLoop(set_as_default=True)
				self._main_loop = GLib.MainLoop()
				self._thread = threading.Thread(target=self._thread_code)
				self._thread.start()
				bus = dbus.SystemBus()
				self._proxy = bus.get_object(self._bus_name, self._interface_name, self._object_name)
		except dbus.exceptions.DBusException:
			raise TunedAdminDBusException("Cannot talk to Tuned daemon via DBus. Is Tuned daemon running?")

	def _thread_code(self):
		self._main_loop.run()

	def _call(self, method_name, *args, **kwargs):
		self._init_proxy()

		try:
			method = self._proxy.get_dbus_method(method_name)
			return method(*args, **kwargs)
		except dbus.exceptions.DBusException as dbus_exception:
			err_str = "DBus call to Tuned daemon failed"
			if self._debug:
				err_str += " (%s)" % str(dbus_exception)
			raise TunedAdminDBusException(err_str)

	def set_signal_handler(self, signal, cb):
		self._init_proxy()
		self._proxy.connect_to_signal(signal, cb)

	def is_running(self):
		return self._call("is_running")

	def start(self):
		return self._call("start")

	def stop(self):
		return self._call("stop")

	def profiles(self):
		return self._call("profiles")

	def profiles2(self):
		return self._call("profiles2")

	def profile_info(self, profile_name):
		return self._call("profile_info", profile_name)

	def active_profile(self):
		return self._call("active_profile")

	def switch_profile(self, new_profile):
		if new_profile == "":
			return (False, "No profile specified")
		return self._call("switch_profile", new_profile)

	def recommend_profile(self):
		return self._call("recommend_profile")

	def verify_profile(self):
		return self._call("verify_profile")

	def verify_profile_ignore_missing(self):
		return self._call("verify_profile_ignore_missing")

	def off(self):
		return self._call("disable")

	def exit(self):
		if self._thread is not None and self._thread.is_alive():
			self._main_loop.quit()
			self._thread.join()
			self._thread = None
