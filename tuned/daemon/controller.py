from tuned import exports
import tuned.logs
import tuned.exceptions
from tuned.exceptions import TunedException
import threading
import tuned.consts as consts
from tuned.utils.commands import commands
from tuned.utils.profile_recommender import ProfileRecommender

__all__ = ["Controller"]

log = tuned.logs.get()

class TimerStore(object):
	def __init__(self):
		self._timers = dict()
		self._timers_lock = threading.Lock()

	def store_timer(self, token, timer):
		with self._timers_lock:
			self._timers[token] = timer

	def drop_timer(self, token):
		with self._timers_lock:
			try:
				timer = self._timers[token]
				timer.cancel()
				del self._timers[token]
			except:
				pass

	def cancel_all(self):
		with self._timers_lock:
			for timer in self._timers.values():
				timer.cancel()
			self._timers.clear()

class Controller(tuned.exports.interfaces.ExportableInterface):
	"""
	Controller's purpose is to keep the program running, start/stop the tuning,
	and export the controller interface (currently only over D-Bus).
	"""

	def __init__(self, daemon, global_config):
		super(Controller, self).__init__()
		self._daemon = daemon
		self._global_config = global_config
		self._terminate = threading.Event()
		self._cmd = commands()
		self._timer_store = TimerStore()

	def run(self):
		"""
		Controller main loop. The call is blocking.
		"""
		log.info("starting controller")
		res = self.start()
		daemon = self._global_config.get_bool(consts.CFG_DAEMON, consts.CFG_DEF_DAEMON)
		if not res and daemon:
			exports.start()

		if daemon:
			self._terminate.clear()
			# we have to pass some timeout, otherwise signals will not work
			while not self._cmd.wait(self._terminate, 3600):
				pass

		log.info("terminating controller")
		self.stop()

	def terminate(self):
		self._terminate.set()

	@exports.signal("sbs")
	def profile_changed(self, profile_name, result, errstr):
		pass

	# exports decorator checks the authorization (currently through polkit), caller is None if
	# no authorization was performed (i.e. the call should process as authorized), string
	# identifying caller (with DBus it's the caller bus name) if authorized and empty
	# string if not authorized, caller must be the last argument

	def _log_capture_abort(self, token):
		tuned.logs.log_capture_finish(token)
		self._timer_store.drop_timer(token)

	@exports.export("ii", "s")
	def log_capture_start(self, log_level, timeout, caller = None):
		if caller == "":
			return ""
		token = tuned.logs.log_capture_start(log_level)
		if token is None:
			return ""
		if timeout > 0:
			timer = threading.Timer(timeout,
					self._log_capture_abort, args = [token])
			self._timer_store.store_timer(token, timer)
			timer.start()
		return "" if token is None else token

	@exports.export("s", "s")
	def log_capture_finish(self, token, caller = None):
		if caller == "":
			return ""
		res = tuned.logs.log_capture_finish(token)
		self._timer_store.drop_timer(token)
		return "" if res is None else res

	@exports.export("", "b")
	def start(self, caller = None):
		if caller == "":
			return False
		if self._global_config.get_bool(consts.CFG_DAEMON, consts.CFG_DEF_DAEMON):
			if self._daemon.is_running():
				return True
			elif not self._daemon.is_enabled():
				return False
		return self._daemon.start()

	@exports.export("", "b")
	def stop(self, caller = None):
		if caller == "":
			return False
		if not self._daemon.is_running():
			res = True
		else:
			res = self._daemon.stop()
		self._timer_store.cancel_all()
		return res

	@exports.export("", "b")
	def reload(self, caller = None):
		if caller == "":
			return False
		if not self._daemon.is_running():
			return False
		else:
			stop_ok = self.stop()
			if not stop_ok:
				return False
			self._daemon.reload_profile_config()
			return self.start()

	def _switch_profile(self, profile_name, manual):
		was_running = self._daemon.is_running()
		msg = "OK"
		success = True
		reapply = False
		try:
			if was_running:
				self._daemon.stop(profile_switch = True)
			self._daemon.set_profile(profile_name, manual)
		except tuned.exceptions.TunedException as e:
			success = False
			msg = str(e)
			if was_running and self._daemon.profile.name == profile_name:
				log.error("Failed to reapply profile '%s'. Did it change on disk and break?" % profile_name)
				reapply = True
			else:
				log.error("Failed to apply profile '%s'" % profile_name)
		finally:
			if was_running:
				if reapply:
					log.warn("Applying previously applied (possibly out-dated) profile '%s'." % profile_name)
				elif not success:
					log.info("Applying previously applied profile.")
				self._daemon.start()

		return (success, msg)

	@exports.export("s", "(bs)")
	def switch_profile(self, profile_name, caller = None):
		if caller == "":
			return (False, "Unauthorized")
		return self._switch_profile(profile_name, True)

	@exports.export("", "(bs)")
	def auto_profile(self, caller = None):
		if caller == "":
			return (False, "Unauthorized")
		profile_name = self.recommend_profile()
		return self._switch_profile(profile_name, False)

	@exports.export("", "s")
	def active_profile(self, caller = None):
		if caller == "":
			return ""
		if self._daemon.profile is not None:
			return self._daemon.profile.name
		else:
			return ""

	@exports.export("", "(ss)")
	def profile_mode(self, caller = None):
		if caller == "":
			return "unknown", "Unauthorized"
		manual = self._daemon.manual
		if manual is None:
			# This means no profile is applied. Check the preset value.
			try:
				profile, manual = self._cmd.get_active_profile()
				if manual is None:
					manual = profile is not None
			except TunedException as e:
				mode = "unknown"
				error = str(e)
				return mode, error
		mode = consts.ACTIVE_PROFILE_MANUAL if manual else consts.ACTIVE_PROFILE_AUTO
		return mode, ""

	@exports.export("", "b")
	def disable(self, caller = None):
		if caller == "":
			return False
		if self._daemon.is_running():
			self._daemon.stop()
		if self._daemon.is_enabled():
			self._daemon.set_profile(None, None, save_instantly=True)
		return True

	@exports.export("", "b")
	def is_running(self, caller = None):
		if caller == "":
			return False
		return self._daemon.is_running()

	@exports.export("", "as")
	def profiles(self, caller = None):
		if caller == "":
			return []
		return self._daemon.profile_loader.profile_locator.get_known_names()

	@exports.export("", "a(ss)")
	def profiles2(self, caller = None):
		if caller == "":
			return []
		return self._daemon.profile_loader.profile_locator.get_known_names_summary()

	@exports.export("s", "(bsss)")
	def profile_info(self, profile_name, caller = None):
		if caller == "":
			return tuple(False, "", "", "")
		if profile_name is None or profile_name == "":
			profile_name = self.active_profile()
		return tuple(self._daemon.profile_loader.profile_locator.get_profile_attrs(profile_name, [consts.PROFILE_ATTR_SUMMARY, consts.PROFILE_ATTR_DESCRIPTION], [""]))

	@exports.export("", "s")
	def recommend_profile(self, caller = None):
		if caller == "":
			return ""
		return ProfileRecommender().recommend(hardcoded = not self._global_config.get_bool(consts.CFG_RECOMMEND_COMMAND, consts.CFG_DEF_RECOMMEND_COMMAND))

	@exports.export("", "b")
	def verify_profile(self, caller = None):
		if caller == "":
			return False
		return self._daemon.verify_profile(ignore_missing = False)

	@exports.export("", "b")
	def verify_profile_ignore_missing(self, caller = None):
		if caller == "":
			return False
		return self._daemon.verify_profile(ignore_missing = True)

	@exports.export("", "a{sa{ss}}")
	def get_all_plugins(self, caller = None):
		"""Return dictionary with accesible plugins

		Return:
		dictionary -- {plugin_name: {parameter_name: default_value}}
		"""
		if caller == "":
			return False
		plugins = {}
		for plugin_class in self._daemon.get_all_plugins():
			plugin_name = plugin_class.__module__.split(".")[-1].split("_", 1)[1]
			conf_options = plugin_class._get_config_options()
			plugins[plugin_name] = {}
			for key, val in conf_options.items():
				plugins[plugin_name][key] = str(val)
		return plugins

	@exports.export("s","s")
	def get_plugin_documentation(self, plugin_name, caller = None):
		"""Return docstring of plugin's class"""
		if caller == "":
			return False
		return self._daemon.get_plugin_documentation(str(plugin_name))

	@exports.export("s","a{ss}")
	def get_plugin_hints(self, plugin_name, caller = None):
		"""Return dictionary with plugin's parameters and their hints

		Parameters:
		plugin_name -- name of plugin

		Return:
		dictionary -- {parameter_name: hint}
		"""
		if caller == "":
			return False
		return self._daemon.get_plugin_hints(str(plugin_name))
