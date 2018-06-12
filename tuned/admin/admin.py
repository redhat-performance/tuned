
from __future__ import print_function
import tuned.admin
from tuned.utils.commands import commands
from tuned.profiles import Locator as profiles_locator
from .exceptions import TunedAdminDBusException
from tuned.exceptions import TunedException
import tuned.consts as consts
import os
import sys
import errno
import time
import threading
import logging

class Admin(object):
	def __init__(self, dbus = True, debug = False, async = False,
			timeout = consts.ADMIN_TIMEOUT,
			log_level = logging.ERROR):
		self._dbus = dbus
		self._debug = debug
		self._async = async
		self._timeout = timeout
		self._cmd = commands(debug)
		self._profiles_locator = profiles_locator(consts.LOAD_DIRECTORIES)
		self._daemon_action_finished = threading.Event()
		self._daemon_action_profile = ""
		self._daemon_action_result = True
		self._daemon_action_errstr = ""
		self._controller = None
		self._log_token = None
		self._log_level = log_level
		if self._dbus:
			self._controller = tuned.admin.DBusController(consts.DBUS_BUS, consts.DBUS_INTERFACE, consts.DBUS_OBJECT, debug)
			try:
				self._controller.set_signal_handler(consts.DBUS_SIGNAL_PROFILE_CHANGED, self._signal_profile_changed_cb)
			except TunedAdminDBusException as e:
				self._error(e)
				self._dbus = False

	def _error(self, message):
		print(message, file=sys.stderr)

	def _signal_profile_changed_cb(self, profile_name, result, errstr):
		# ignore successive signals if the signal is not yet processed
		if not self._daemon_action_finished.is_set():
			self._daemon_action_profile = profile_name
			self._daemon_action_result = result
			self._daemon_action_errstr = errstr
			self._daemon_action_finished.set()

	def _tuned_is_running(self):
		try:
			os.kill(int(self._cmd.read_file(consts.PID_FILE)), 0)
		except OSError as e:
			return e.errno == errno.EPERM
		except (ValueError, IOError) as e:
			return False
		return True

	# run the action specified by the action_name with args
	def action(self, action_name, *args, **kwargs):
		if action_name is None or action_name == "":
			return False
		action = None
		action_dbus = None
		res = False
		try:
			action_dbus = getattr(self, "_action_dbus_" + action_name)
		except AttributeError as e:
			self._dbus = False
		try:
			action = getattr(self, "_action_" + action_name)
		except AttributeError as e:
			if not self._dbus:
				self._error(e + ", action '%s' is not implemented" % action_name)
				return False
		if self._dbus:
			try:
				self._controller.set_on_exit_action(
						self._log_capture_finish)
				self._controller.set_action(action_dbus, *args, **kwargs)
				res = self._controller.run()
			except TunedAdminDBusException as e:
				self._error(e)
				self._dbus = False

		if not self._dbus:
			res = action(*args, **kwargs)
		return res

	def _print_profiles(self, profile_names):
		print("Available profiles:")
		for profile in profile_names:
			if profile[1] is not None and profile[1] != "":
				print(self._cmd.align_str("- %s" % profile[0], 30, "- %s" % profile[1]))
			else:
				print("- %s" % profile[0])

	def _action_dbus_list(self):
		try:
			profile_names = self._controller.profiles2()
		except TunedAdminDBusException as e:
			# fallback to older API
			profile_names = [(profile, "") for profile in self._controller.profiles()]
		self._print_profiles(profile_names)
		self._action_dbus_active()
		return self._controller.exit(True)

	def _action_list(self):
		self._print_profiles(self._profiles_locator.get_known_names_summary())
		self._action_active()
		return True

	def _dbus_get_active_profile(self):
		profile_name = self._controller.active_profile()
		if profile_name == "":
			profile_name = None
		self._controller.exit(True)
		return profile_name

	def _get_active_profile(self):
		profile_name, manual = self._cmd.get_active_profile()
		return profile_name

	def _get_profile_mode(self):
		(profile, manual) = self._cmd.get_active_profile()
		if manual is None:
			manual = profile is not None
		return consts.ACTIVE_PROFILE_MANUAL if manual else consts.ACTIVE_PROFILE_AUTO

	def _print_profile_info(self, profile, profile_info):
		if profile_info[0] == True:
			print("Profile name:")
			print(profile_info[1])
			print()
			print("Profile summary:")
			print(profile_info[2])
			print()
			print("Profile description:")
			print(profile_info[3])
			return True
		else:
			print("Unable to get information about profile '%s'" % profile)
			return False

	def _action_dbus_profile_info(self, profile = ""):
		if profile == "":
			profile = self._dbus_get_active_profile()
		return self._controller.exit(self._print_profile_info(profile, self._controller.profile_info(profile)))

	def _action_profile_info(self, profile = ""):
		if profile == "":
			try:
				profile = self._get_active_profile()
				if profile is None:
					print("No current active profile.")
					return False
			except TunedException as e:
				self._error(str(e))
				return False
		return self._print_profile_info(profile, self._profiles_locator.get_profile_attrs(profile, [consts.PROFILE_ATTR_SUMMARY, consts.PROFILE_ATTR_DESCRIPTION], ["", ""]))

	def _print_profile_name(self, profile_name):
		if profile_name is None:
			print("No current active profile.")
			return False
		else:
			print("Current active profile: %s" % profile_name)
		return True

	def _action_dbus_active(self):
		return self._controller.exit(self._print_profile_name(self._dbus_get_active_profile()))

	def _action_active(self):
		try:
			profile_name = self._get_active_profile()
		except TunedException as e:
			self._error(str(e))
			return False
		if profile_name is not None and not self._tuned_is_running():
			print("It seems that tuned daemon is not running, preset profile is not activated.")
			print("Preset profile: %s" % profile_name)
			return True
		return self._print_profile_name(profile_name)

	def _print_profile_mode(self, mode):
		print("Profile selection mode: " + mode)

	def _action_dbus_profile_mode(self):
		mode, error = self._controller.profile_mode()
		self._print_profile_mode(mode)
		if error != "":
			self._error(error)
			return self._controller.exit(False)
		return self._controller.exit(True)

	def _action_profile_mode(self):
		try:
			mode = self._get_profile_mode()
			self._print_profile_mode(mode)
			return True
		except TunedException as e:
			self._error(str(e))
			return False

	def _profile_print_status(self, ret, msg):
		if ret:
			if not self._controller.is_running() and not self._controller.start():
				self._error("Cannot enable the tuning.")
				ret = False
		else:
			self._error(msg)
		return ret

	def _action_dbus_wait_profile(self, profile_name):
		if time.time() >= self._timestamp + self._timeout:
			print("Operation timed out after waiting %d seconds(s), you may try to increase timeout by using --timeout command line option or using --async." % self._timeout)
			return self._controller.exit(False)
		if self._daemon_action_finished.isSet():
			if self._daemon_action_profile == profile_name:
				if not self._daemon_action_result:
					print("Error changing profile: %s" % self._daemon_action_errstr)
					return self._controller.exit(False)
				return self._controller.exit(True)
		return False

	def _log_capture_finish(self):
		if self._log_token is None or self._log_token == "":
			return
		try:
			log_msgs = self._controller.log_capture_finish(
					self._log_token)
			self._log_token = None
			print(log_msgs, end = "", file = sys.stderr)
			sys.stderr.flush()
		except TunedAdminDBusException as e:
			self._error("Error: Failed to stop log capture. Restart the Tuned daemon to prevent a memory leak.")

	def _action_dbus_profile(self, profiles):
		if len(profiles) == 0:
			return self._action_dbus_list()
		profile_name = " ".join(profiles)
		if profile_name == "":
			return self._controller.exit(False)
		self._daemon_action_finished.clear()
		if not self._async and self._log_level is not None:
			# 25 seconds default DBus timeout + 5 secs safety margin
			timeout = self._timeout + 25 + 5
			self._log_token = self._controller.log_capture_start(
					self._log_level, timeout)
		(ret, msg) = self._controller.switch_profile(profile_name)
		if self._async or not ret:
			return self._controller.exit(self._profile_print_status(ret, msg))
		else:
			self._timestamp = time.time()
			self._controller.set_action(self._action_dbus_wait_profile, profile_name)
		return self._profile_print_status(ret, msg)

	def _restart_tuned(self):
		print("Trying to (re)start tuned...")
		(ret, msg) = self._cmd.execute(["service", "tuned", "restart"])
		if ret == 0:
			print("Tuned (re)started, changes applied.")
		else:
			print("Tuned (re)start failed, you need to (re)start tuned by hand for changes to apply.")

	def _set_profile(self, profile_name, manual):
		if profile_name in self._profiles_locator.get_known_names():
			try:
				self._cmd.save_active_profile(profile_name, manual)
				self._restart_tuned()
				return True
			except TunedException as e:
				self._error(str(e))
				self._error("Unable to switch profile.")
				return False
		else:
			self._error("Requested profile '%s' doesn't exist." % profile_name)
			return False

	def _action_profile(self, profiles):
		if len(profiles) == 0:
			return self._action_list()
		profile_name = " ".join(profiles)
		if profile_name == "":
			return False
		return self._set_profile(profile_name, True)

	def _action_dbus_auto_profile(self):
		profile_name = self._controller.recommend_profile()
		self._daemon_action_finished.clear()
		if not self._async and self._log_level is not None:
			# 25 seconds default DBus timeout + 5 secs safety margin
			timeout = self._timeout + 25 + 5
			self._log_token = self._controller.log_capture_start(
					self._log_level, timeout)
		(ret, msg) = self._controller.auto_profile()
		if self._async or not ret:
			return self._controller.exit(self._profile_print_status(ret, msg))
		else:
			self._timestamp = time.time()
			self._controller.set_action(self._action_dbus_wait_profile, profile_name)
		return self._profile_print_status(ret, msg)

	def _action_auto_profile(self):
		profile_name = self._cmd.recommend_profile()
		return self._set_profile(profile_name, False)

	def _action_dbus_recommend_profile(self):
		print(self._controller.recommend_profile())
		return self._controller.exit(True)

	def _action_recommend_profile(self):
		print(self._cmd.recommend_profile())
		return True

	def _action_dbus_verify_profile(self, ignore_missing):
		if ignore_missing:
			ret = self._controller.verify_profile_ignore_missing()
		else:
			ret = self._controller.verify_profile()
		if ret:
			print("Verfication succeeded, current system settings match the preset profile.")
		else:
			print("Verification failed, current system settings differ from the preset profile.")
			print("You can mostly fix this by restarting the Tuned daemon, e.g.:")
			print("  systemctl restart tuned")
			print("or")
			print("  service tuned restart")
			print("Sometimes (if some plugins like bootloader are used) a reboot may be required.")
		print("See tuned log file ('%s') for details." % consts.LOG_FILE)
		return self._controller.exit(ret)

	def _action_verify_profile(self, ignore_missing):
		print("Not supported in no_daemon mode.")
		return False

	def _action_dbus_off(self):
		# 25 seconds default DBus timeout + 5 secs safety margin
		timeout = 25 + 5
		self._log_token = self._controller.log_capture_start(
				self._log_level, timeout)
		ret = self._controller.off()
		if not ret:
			self._error("Cannot disable active profile.")
		return self._controller.exit(ret)

	def _action_off(self):
		print("Not supported in no_daemon mode.")
		return False
