import tuned.utils.commands
from tuned.profiles import Locator as profiles_locator
from exceptions import TunedAdminDBusException
import tuned.consts as consts
import sys

class Admin(object):
	def __init__(self, controller):
		self._controller = controller

	def _error(self, message):
		print >>sys.stderr, message

	def list(self, dbus_warn = True):
		try:
			profile_names = self._controller.profiles()
		except TunedAdminDBusException as e:
			if dbus_warn:
				print >> sys.stderr, e
			profile_names = profiles_locator(consts.LOAD_DIRECTORIES).get_known_names()
		print "Available profiles:"
		for profile in profile_names:
			print "- %s" % profile
		self.active(False)

	def active(self, dbus_warn = True):
		try:
			profile_name = self._controller.active_profile()
		except TunedAdminDBusException as e:
			if dbus_warn:
				print >> sys.stderr, e
			profile_name = tuned.utils.commands.read_file(consts.ACTIVE_PROFILE_FILE, None)
		if profile_name is not None and profile_name != "":
			print "Current active profile: %s" % profile_name
			return True
		else:
			print "No current active profile."
			return False

	def profile(self, profiles, dbus_warn = True):
		fallback = False
		profile_name = " ".join(profiles)
		if profile_name == "":
			return False
		try:
			ret = self._controller.switch_profile(profile_name)
		except TunedAdminDBusException as e:
			fallback = True
			if dbus_warn:
				print >> sys.stderr, e
			if profile_name in profiles_locator(consts.LOAD_DIRECTORIES).get_known_names():
				ret = tuned.utils.commands.write_to_file(consts.ACTIVE_PROFILE_FILE, profile_name)
			else:
				ret = False
				self._error("Requested profile '%s' doesn't exist." % profile_name)
		if ret:
			if fallback:
				print "You need to (re)start the tuned daemon by hand for changes to apply."
			else:
				if not self._controller.is_running() and not self._controller.start():
					self._error("Cannot enable the tuning.")
					ret = False
		else:
			self._error("Cannot switch the profile.")

		return ret

	def recommend_profile(self, dbus_warn = True):
		try:
			profile = self._controller.recommend_profile()
		except TunedAdminDBusException as e:
			if dbus_warn:
				print >> sys.stderr, e
			profile = tuned.utils.commands.recommend_profile()
		print profile

	def off(self):
		result = self._controller.off()
		if not result:
			self._error("Cannot disable active profile.")
		return result
