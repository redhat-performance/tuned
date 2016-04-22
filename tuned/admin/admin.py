from tuned.utils.commands import commands
from tuned.profiles import Locator as profiles_locator
from exceptions import TunedAdminDBusException
import tuned.consts as consts
import os
import sys
import errno
import threading

class Admin(object):
	def __init__(self, controller, debug = False, async = False):
		self._controller = controller
		self._debug = debug
		self._async = async
		self._cmd = commands(debug)
		self._profiles_locator = profiles_locator(consts.LOAD_DIRECTORIES)
		self._daemon_action_finished = threading.Event()
		self._daemon_action_profile = ""
		self._daemon_action_result = True
		self._daemon_action_errstr = ""
		if self._controller is None:
			self._dbus = False
		else:
			self._dbus = True
			try:
				self._controller.set_signal_handler(consts.DBUS_SIGNAL_PROFILE_CHANGED, self._signal_profile_changed_cb)
			except TunedAdminDBusException as e:
				self._error(e)
				self._dbus = False

	def _error(self, message):
		print >>sys.stderr, message

	def _signal_profile_changed_cb(self, profile_name, result, errstr):
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

	def list(self):
		if self._dbus:
			try:
				profile_names = self._controller.profiles2()
			except TunedAdminDBusException as e:
				# fallback to older API
				try:
					profile_names = self._controller.profiles()
				except TunedAdminDBusException as e:
					self._error(e)
					self._dbus = False
				profile_names = map(lambda profile:(profile, ""), profile_names)
		if not self._dbus:
			profile_names = self._profiles_locator.get_known_names_summary()
		print "Available profiles:"
		for profile in profile_names:
			if profile[1] is not None and profile[1] != "":
				print self._cmd.align_str("- %s" % profile[0], 30, "- %s" % profile[1])
			else:
				print "- %s" % profile[0]
		self.active()

	def _get_active_profile(self):
		profile_name = None
		if self._dbus:
			try:
				profile_name = self._controller.active_profile()
			except TunedAdminDBusException as e:
				self._error(e)
				self._dbus = False
		if not self._dbus:
			profile_name = str.strip(self._cmd.read_file(consts.ACTIVE_PROFILE_FILE, None))
		if profile_name == "":
			profile_name = None
		return profile_name

	def profile_info(self, profile = ""):
		if profile == "":
			profile = self._get_active_profile()
		if self._dbus:
			try:
				ret = self._controller.profile_info(profile)
			except TunedAdminDBusException as e:
				self._error(e)
				self._dbus = False
		if not self._dbus:
			ret = self._profiles_locator.get_profile_attrs(profile, [consts.PROFILE_ATTR_SUMMARY, consts.PROFILE_ATTR_DESCRIPTION], ["", ""])
		if ret[0] == True:
			print "Profile name:"
			print ret[1]
			print
			print "Profile summary:"
			print ret[2]
			print
			print "Profile description:"
			print ret[3]
			return True
		else:
			print "Unable to get information about profile '%s'" % profile
			return False

	def active(self):
		profile_name = self._get_active_profile()
		if profile_name is not None:
			if self._controller is not None and self._tuned_is_running():
				print "Current active profile: %s" % profile_name
			else:
				if self._controller is not None:
					print "It seems that tuned daemon is not running, preset profile is not activated."
				print "Preset profile: %s" % profile_name
			return True
		else:
			print "No current active profile."
			return False

	def profile(self, profiles):
		profile_name = " ".join(profiles)
		if profile_name == "":
			return False
		if self._dbus:
			self._daemon_action_finished.clear()
			try:
				(ret, msg) = self._controller.switch_profile(profile_name)
			except TunedAdminDBusException as e:
				self._error(e)
				self._dbus = False
			if self._dbus and not self._async:
				waiting = True
				while waiting:
					if self._daemon_action_finished.wait(consts.ADMIN_TIMEOUT):
						if self._daemon_action_profile == profile_name:
							waiting = False
							if not self._daemon_action_result:
								print "Error changing profile: %s" % self._daemon_action_errstr
								return False
					else:
						print "Operation timed out"
						return False
		if not self._dbus:
			if profile_name in self._profiles_locator.get_known_names():
				if self._cmd.write_to_file(consts.ACTIVE_PROFILE_FILE, profile_name):
					print "Trying to (re)start tuned..."
					(ret, out) = self._cmd.execute(["service", "tuned", "restart"])
					if ret == 0:
						print "Tuned (re)started, changes applied."
					else:
						print "Tuned (re)start failed, you need to (re)start tuned by hand for changes to apply."
					return True
				else:
					self._error("Unable to switch profile, do you have enough permissions?")
					return False
			else:
				self._error("Requested profile '%s' doesn't exist." % profile_name)
				return False
		if ret:
			if not self._controller.is_running() and not self._controller.start():
				self._error("Cannot enable the tuning.")
				ret = False
		else:
			self._error(msg)

		return ret

	def recommend_profile(self):
		if self._dbus:
			try:
				profile = self._controller.recommend_profile()
			except TunedAdminDBusException as e:
				self._error(e)
				self._dbus = False
		if not self._dbus:
			profile = self._cmd.recommend_profile()
		print profile

	def verify_profile(self):
		ret = False
		if self._controller is None:
			print "Not supported in no_daemon mode."
			return False
		try:
			ret = self._controller.verify_profile()
		except TunedAdminDBusException as e:
			self._error(e)
			self._error("Cannot verify profile if there is no connection to daemon")
			return False

		if ret:
			print "Verfication succeeded, current system settings match the preset profile."
		else:
			print "Verification failed, current system settings differ from the preset profile."
			print "You can mostly fix this by Tuned restart, e.g.:"
			print "  service tuned restart"
		print "See tuned log file ('%s') for details." % consts.LOG_FILE
		return ret

	def off(self):
		if self._controller is None:
			print "Not supported in no_daemon mode."
			return False
		try:
			result = self._controller.off()
		except TunedAdminDBusException as e:
			self._error(e)
			return False
		if not result:
			self._error("Cannot disable active profile.")
		return result
