import dbus
import dbus.exceptions
import tuned.utils.commands
from exceptions import TunedAdminException

__all__ = ["DBusController"]

class DBusController(object):
	def __init__(self, bus_name, interface_name, object_name):
		self._bus_name = bus_name
		self._interface_name = interface_name
		self._object_name = object_name
		self._proxy = None

	def _init_proxy(self):
		if self._proxy is None:
			bus = dbus.SystemBus()
			self._proxy = bus.get_object(self._bus_name, self._interface_name, self._object_name)

	def _call(self, method_name, *args, **kwargs):
		try:
			self._init_proxy()
		except dbus.exceptions.DBusException:
			raise TunedAdminException("Cannot talk to Tuned daemon via DBus.")

		try:
			method = self._proxy.get_dbus_method(method_name)
			return method(*args, **kwargs)
		except dbus.exceptions.DBusException as dbus_exception:
			raise TunedAdminException("DBus call to Tuned daemon failed (%s)." % str(dbus_exception))

	def is_running(self):
		return self._call("is_running")

	def start(self):
		return self._call("start")

	def stop(self):
		return self._call("stop")

	def profiles(self):
		return self._call("profiles")

	def active_profile(self):
		profile_name = self._call("active_profile")
		if profile_name != "":
			return profile_name
		else:
			return None

	def switch_profile(self, new_profile):
		if new_profile != "":
			return self._call("switch_profile", new_profile)
		else:
			return False

	def recommend_profile(self):
		try:
			profile = self._call("recommend_profile")
		except TunedAdminException:
			profile = tuned.utils.commands.recommend_profile()
		return profile

	def off(self):
		return self._call("disable")
