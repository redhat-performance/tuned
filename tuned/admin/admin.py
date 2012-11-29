import sys

class Admin(object):
	def __init__(self, controller):
		self._controller = controller

	def _error(self, message):
		print >>sys.stderr, message

	def list(self):
		profiles = self._controller.profiles()
		print "Available profiles:"
		for profile in profiles:
			print "- %s" % profile
		self.active()

	def active(self):
		profile = self._controller.active_profile()
		if profile is not None:
			print "Current active profile: %s" % profile
			return True
		else:
			print "No current active profile."
			return False

	def profile(self, profiles):
		profile_name = " ".join(profiles)
		if not self._controller.switch_profile(profile_name):
			self._error("Cannot switch the profile.")
			return False

		if not self._controller.is_running():
			if not self._controller.start():
				self._error("Cannot enable the tuning.")
				return False

		return True

	def recommend_profile(self):
		print self._controller.recommend_profile()

	def off(self):
		result = self._controller.off()
		if not result:
			self._error("Cannot disable active profile.")
		return result
