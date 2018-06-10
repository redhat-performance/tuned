import dbus
import dbus.exceptions
import time
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib, GObject
from .exceptions import TunedAdminDBusException

__all__ = ["DBusController"]

class DBusController(object):
	def __init__(self, bus_name, interface_name, object_name, debug = False):
		self._bus_name = bus_name
		self._interface_name = interface_name
		self._object_name = object_name
		self._proxy = None
		self._interface = None
		self._debug = debug
		self._main_loop = None
		self._action = None
		self._on_exit_action = None
		self._ret = True
		self._exit = False
		self._exception = None

	def _init_proxy(self):
		try:
			if self._proxy is None:
				DBusGMainLoop(set_as_default=True)
				self._main_loop = GLib.MainLoop()
				bus = dbus.SystemBus()
				self._proxy = bus.get_object(self._bus_name, self._object_name)
				self._interface = dbus.Interface(self._proxy, dbus_interface = self._interface_name)
		except dbus.exceptions.DBusException:
			raise TunedAdminDBusException("Cannot talk to Tuned daemon via DBus. Is Tuned daemon running?")

	def _idle(self):
		if self._action is not None:
			# This may (and very probably will) run in child thread, so catch and pass exceptions to the main thread
			try:
				self._action_exit_code = self._action(*self._action_args, **self._action_kwargs)
			except TunedAdminDBusException as e:
				self._exception = e
				self._exit = True

		if self._exit:
			if self._on_exit_action is not None:
				self._on_exit_action(*self._on_exit_action_args,
						**self._on_exit_action_kwargs)
			self._main_loop.quit()
			return False
		else:
			time.sleep(1)
		return True

	def set_on_exit_action(self, action, *args, **kwargs):
		self._on_exit_action = action
		self._on_exit_action_args = args
		self._on_exit_action_kwargs = kwargs

	def set_action(self, action, *args, **kwargs):
		self._action = action
		self._action_args = args
		self._action_kwargs = kwargs

	def run(self):
		self._exception = None
		GLib.idle_add(self._idle)
		self._main_loop.run()
		# Pass exception happened in child thread to the caller
		if self._exception is not None:
			raise self._exception
		return self._ret

	def _call(self, method_name, *args, **kwargs):
		self._init_proxy()

		try:
			method = self._interface.get_dbus_method(method_name)
			return method(*args, timeout=40)
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

	def log_capture_start(self, log_level, timeout):
		return self._call("log_capture_start", log_level, timeout)

	def log_capture_finish(self, token):
		return self._call("log_capture_finish", token)

	def active_profile(self):
		return self._call("active_profile")

	def profile_mode(self):
		return self._call("profile_mode")

	def switch_profile(self, new_profile):
		if new_profile == "":
			return (False, "No profile specified")
		return self._call("switch_profile", new_profile)

	def auto_profile(self):
		return self._call("auto_profile")

	def recommend_profile(self):
		return self._call("recommend_profile")

	def verify_profile(self):
		return self._call("verify_profile")

	def verify_profile_ignore_missing(self):
		return self._call("verify_profile_ignore_missing")

	def off(self):
		return self._call("disable")

	def exit(self, ret):
		self.set_action(None)
		self._ret = ret
		self._exit = True
		return ret
