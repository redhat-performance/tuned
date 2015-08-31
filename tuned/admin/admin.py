from tuned.utils.commands import commands
from tuned.profiles import Locator as profiles_locator
from exceptions import TunedAdminDBusException
import tuned.consts as consts
import os
import sys
import errno

class Admin(object):
	def __init__(self, controller, debug = False):
		self._controller = controller
		self._debug = debug
		self._cmd = commands(debug)

	def _error(self, message):
		print >>sys.stderr, message

	def _tuned_is_running(self):
		try:
			os.kill(int(self._cmd.read_file(consts.PID_FILE)), 0)
		except OSError as e:
			return e.errno == errno.EPERM
		except (ValueError, IOError) as e:
			return False
		return True

	def list(self):
		no_dbus = self._controller is None
		if not no_dbus:
			try:
				profile_names = self._controller.profiles()
			except TunedAdminDBusException as e:
				self._error(e)
				no_dbus = True
		if no_dbus:
			profile_names = profiles_locator(consts.LOAD_DIRECTORIES).get_known_names()
		print "Available profiles:"
		for profile in profile_names:
			print "- %s" % profile
		self.active()

	def active(self):
		no_dbus = self._controller is None
		if not no_dbus:
			try:
				profile_name = self._controller.active_profile()
			except TunedAdminDBusException as e:
				self._error(e)
				no_dbus = True
		if no_dbus:
			profile_name = str.strip(self._cmd.read_file(consts.ACTIVE_PROFILE_FILE, None))
		if profile_name is not None and profile_name != "":
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
		no_dbus = self._controller is None
		profile_name = " ".join(profiles)
		if profile_name == "":
			return False
		if not no_dbus:
			try:
				(ret, msg) = self._controller.switch_profile(profile_name)
			except TunedAdminDBusException as e:
				self._error(e)
				no_dbus = True
		if no_dbus:
			if profile_name in profiles_locator(consts.LOAD_DIRECTORIES).get_known_names():
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
		no_dbus = self._controller is None
		if not no_dbus:
			try:
				profile = self._controller.recommend_profile()
			except TunedAdminDBusException as e:
				self._error(e)
				no_dbus = True
		if no_dbus:
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
