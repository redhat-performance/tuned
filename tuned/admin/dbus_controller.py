import dbus
import dbus.exceptions
from exceptions import TunedAdminDBusException

__all__ = ["DBusController"]

class DBusController(object):
	def __init__(self, bus_name, interface_name, object_name, debug = False):
		self._bus_name = bus_name
		self._interface_name = interface_name
		self._object_name = object_name
		self._proxy = None
		self._debug = debug

	def _init_proxy(self):
		if self._proxy is None:
			bus = dbus.SystemBus()
			self._proxy = bus.get_object(self._bus_name, self._interface_name, self._object_name)

	def _call(self, method_name, *args, **kwargs):
		try:
			self._init_proxy()
		except dbus.exceptions.DBusException:
			raise TunedAdminDBusException("Cannot talk to Tuned daemon via DBus. Is Tuned daemon running?")

		try:
			method = self._proxy.get_dbus_method(method_name)
			return method(*args, **kwargs)
		except dbus.exceptions.DBusException as dbus_exception:
			err_str = "DBus call to Tuned daemon failed"
			if self._debug:
				err_str += " (%s)" % str(dbus_exception)
			raise TunedAdminDBusException(err_str)

	def is_running(self):
		return self._call("is_running")

	def start(self):
		return self._call("start")

	def stop(self):
		return self._call("stop")

	def profiles(self):
		return self._call("profiles")

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

	def off(self):
		return self._call("disable")
