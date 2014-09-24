from tuned.utils.commands import commands
from tuned.profiles import Locator as profiles_locator
from exceptions import TunedAdminDBusException
import tuned.consts as consts
import sys

class Admin(object):
	def __init__(self, controller, debug = False):
		self._controller = controller
		self._debug = debug
		self._cmd = commands(debug)

	def _error(self, message):
		print >>sys.stderr, message

	def list(self):
		try:
			profile_names = self._controller.profiles()
		except TunedAdminDBusException as e:
			self._error(e)
			profile_names = profiles_locator(consts.LOAD_DIRECTORIES).get_known_names()
		print "Available profiles:"
		for profile in profile_names:
			print "- %s" % profile
		self.active(False)

	def active(self):
		try:
			profile_name = self._controller.active_profile()
		except TunedAdminDBusException as e:
			self._error(e)
			profile_name = self._cmd.read_file(consts.ACTIVE_PROFILE_FILE, None)
		if profile_name is not None and profile_name != "":
			print "Current active profile: %s" % profile_name
			return True
		else:
			print "No current active profile."
			return False

	def profile(self, profiles):
		profile_name = " ".join(profiles)
		if profile_name == "":
			return False
		try:
			(ret, msg) = self._controller.switch_profile(profile_name)
		except TunedAdminDBusException as e:
			self._error(e)
			if profile_name in profiles_locator(consts.LOAD_DIRECTORIES).get_known_names():
				if self._cmd.write_to_file(consts.ACTIVE_PROFILE_FILE, profile_name):
					print "You need to (re)start the tuned daemon by hand for changes to apply."
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
		try:
			profile = self._controller.recommend_profile()
		except TunedAdminDBusException as e:
			self._error(e)
			profile = self._cmd.recommend_profile()
		print profile

	def off(self):
		result = self._controller.off()
		if not result:
			self._error("Cannot disable active profile.")
		return result
