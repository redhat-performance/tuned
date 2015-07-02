from tuned import exports
import tuned.logs
import tuned.exceptions
import threading
import tuned.consts as consts
from tuned.utils.commands import commands

__all__ = ["Controller"]

log = tuned.logs.get()

class Controller(tuned.exports.interfaces.ExportableInterface):
	"""
	Controller's purpose is to keep the program running, start/stop the tuning,
	and export the controller interface (currently only over D-Bus).
	"""

	def __init__(self, daemon, global_config):
		super(self.__class__, self).__init__()
		self._daemon = daemon
		self._global_config = global_config
		self._terminate = threading.Event()
		self._cmd = commands()

	def run(self):
		"""
		Controller main loop. The call is blocking.
		"""
		log.info("starting controller")
		self.start()

		if self._global_config.get_bool(consts.CFG_DAEMON, consts.CFG_DEF_DAEMON):
			self._terminate.clear()
			# we have to pass some timeout, otherwise signals will not work
			while not self._cmd.wait(self._terminate, 3600):
				pass

		log.info("terminating controller")
		self.stop()

	def terminate(self):
		self._terminate.set()

	@exports.export("", "b")
	def start(self):
		if self._global_config.get_bool(consts.CFG_DAEMON, consts.CFG_DEF_DAEMON):
			if self._daemon.is_running():
				return True
			elif not self._daemon.is_enabled():
				return False
		return self._daemon.start()

	@exports.export("", "b")
	def stop(self):
		if not self._daemon.is_running():
			return True
		else:
			return self._daemon.stop()

	@exports.export("", "b")
	def reload(self):
		if not self._daemon.is_running():
			return False
		else:
			return self.stop() and self.start()

	@exports.export("s", "(bs)")
	def switch_profile(self, profile_name):
		was_running = self._daemon.is_running()
		msg = "OK"
		success = True
		try:
			if was_running:
				# stop(switch_profile = True), due to profile switch
				self._daemon.stop(True)
			self._daemon.set_profile(profile_name)
		except tuned.exceptions.TunedException as e:
			success = False
			msg = str(e)
		finally:
			if was_running:
				self._daemon.start()

		return (success, msg)

	@exports.export("", "s")
	def active_profile(self):
		if self._daemon.profile is not None:
			return self._daemon.profile.name
		else:
			return ""

	@exports.export("", "b")
	def disable(self):
		if self._daemon.is_running():
			self._daemon.stop()
		if self._daemon.is_enabled():
			self._daemon.set_profile(None, save_instantly=True)
		return True

	@exports.export("", "b")
	def is_running(self):
		return self._daemon.is_running()

	@exports.export("", "as")
	def profiles(self):
		return self._daemon.profile_loader.profile_locator.get_known_names()

	@exports.export("", "s")
	def recommend_profile(self):
		return self._cmd.recommend_profile(hardcoded = not self._global_config.get_bool(consts.CFG_RECOMMEND_COMMAND, consts.CFG_DEF_RECOMMEND_COMMAND))

	@exports.export("", "b")
	def verify_profile(self):
		return self._daemon.verify_profile()
