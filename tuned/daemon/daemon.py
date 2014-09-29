import os
import errno
import threading
import tuned.logs
from tuned.exceptions import TunedException
import tuned.consts as consts
from tuned.utils.commands import commands

log = tuned.logs.get()


class Daemon(object):
	def __init__(self, unit_manager, profile_loader, profile_name=None, config=None):
		log.debug("initializing daemon")
		self._sleep_interval = int(consts.CFG_DEF_SLEEP_INTERVAL)
		self._update_interval = int(consts.CFG_DEF_UPDATE_INTERVAL)
		self._dynamic_tuning = consts.CFG_DEF_DYNAMIC_TUNING
		if config is not None:
			self._sleep_interval = int(config.get("sleep_interval", consts.CFG_DEF_SLEEP_INTERVAL))
			self._update_interval = int(config.get("update_interval", consts.CFG_DEF_UPDATE_INTERVAL))
			self._dynamic_tuning = config.get("dynamic_tuning", consts.CFG_DEF_DYNAMIC_TUNING)
		if self._sleep_interval <= 0:
			self._sleep_interval = int(consts.CFG_DEF_SLEEP_INTERVAL)
		if self._update_interval == 0:
			self._dynamic_tuning = False
		elif self._update_interval < self._sleep_interval:
			self._update_interval = self._sleep_interval
		self._sleep_cycles = self._update_interval // self._sleep_interval
		log.info("using sleep interval of %d second(s)" % self._sleep_interval)
		if self._dynamic_tuning:
			log.info("dynamic tuning is enabled (can be overriden by plugins)")
			log.info("using update interval of %d second(s) (%d times of the sleep interval)" % (self._sleep_cycles * self._sleep_interval, self._sleep_cycles))

		self._unit_manager = unit_manager
		self._profile_loader = profile_loader
		self._init_threads()
		self._cmd = commands()
		try:
			self._init_profile(profile_name)
		except TunedException as e:
			log.error("Cannot set initial profile. No tunings will be enabled!")

	def _init_threads(self):
		self._thread = None
		self._terminate = threading.Event()
		# Flag which is set if terminating due to profile_switch
		self._terminate_profile_switch = threading.Event()

	def _init_profile(self, profile_name):
		if profile_name is None:
			profile_name = self._get_active_profile()

		self._profile = None
		self.set_profile(profile_name)

	def set_profile(self, profile_name, save_instantly=False):
		if self.is_running():
			raise TunedException("Cannot set profile while the daemon is running.")

		if profile_name == "" or profile_name is None:
			self._profile = None
		elif profile_name not in self.profile_loader.profile_locator.get_known_names():
			raise TunedException("Requested profile '%s' doesn't exist." % profile_name)
		else:
			try:
				self._profile = self._profile_loader.load(profile_name)
			except:
				raise TunedException("Cannot load profile '%s'." % profile_name)

		if save_instantly:
			if profile_name is None:
				profile_name = ""
			self._save_active_profile(profile_name)

	@property
	def profile(self):
		return self._profile

	@property
	def profile_loader(self):
		return self._profile_loader

	def _thread_code(self):
		if self._profile is None:
			raise TunedException("Cannot start the daemon without setting a profile.")

		self._unit_manager.create(self._profile.units)
		self._save_active_profile(self._profile.name)
		self._unit_manager.start_tuning()

		# In python 2 interpreter with applied patch for rhbz#917709 we need to periodically
		# poll, otherwise the python will not have chance to update events / locks (due to GIL)
		# and e.g. DBus control will not work. The polling interval of 1 seconds (which is
		# the default) is still much better than 50 ms polling with unpatched interpreter.
		# For more details see tuned rhbz#917587.
		_sleep_cnt = self._sleep_cycles
		while not self._cmd.wait(self._terminate, self._sleep_interval):
			if self._dynamic_tuning:
				_sleep_cnt -= 1
				if _sleep_cnt <= 0:
					_sleep_cnt = self._sleep_cycles
					log.debug("updating monitors")
					self._unit_manager.update_monitors()
					log.debug("performing tunings")
					self._unit_manager.update_tuning()

		# if terminating due to profile switch
		if self._terminate_profile_switch.is_set():
			profile_switch = True
		else:
			profile_switch = False
		self._unit_manager.stop_tuning(profile_switch)
		self._unit_manager.destroy_all()

	def _save_active_profile(self, profile_name):
		try:
			with open(consts.ACTIVE_PROFILE_FILE, "w") as f:
				f.write(profile_name + "\n")
		except (OSError,IOError) as e:
			log.error("Cannot write active profile into %s: %s" % (consts.ACTIVE_PROFILE_FILE, str(e)))

	def _set_recommended_profile(self):
		log.info("no profile preset, checking what is recommended for your configuration")
		profile = self._cmd.recommend_profile()
		log.info("using '%s' profile and setting it as active" % profile)
		self._save_active_profile(profile)
		return profile

	def _get_active_profile(self):
		try:
			with open(consts.ACTIVE_PROFILE_FILE, "r") as f:
				profile = f.read().strip()
				if profile == "":
					profile = self._set_recommended_profile()
				return profile
		except IOError as e:
			if e.errno == errno.ENOENT:
				# No such file or directory
				profile = self._set_recommended_profile()
			else:
				profile = consts.DEFAULT_PROFILE
				log.error("error reading active profile from '%s', falling back to '%s' profile" % (consts.ACTIVE_PROFILE_FILE, profile))
			return profile
		except (OSError, EOFError) as e:
			log.error("cannot read active profile, falling back to '%s' profile" % consts.DEFAULT_PROFILE)
			return consts.DEFAULT_PROFILE

	def is_enabled(self):
		return self._profile is not None

	def is_running(self):
		return self._thread is not None and self._thread.is_alive()

	def start(self):
		if self.is_running():
			return False

		if self._profile is None:
			return False

		log.info("starting tuning")
		self._thread = threading.Thread(target=self._thread_code)
		self._terminate_profile_switch.clear()
		self._terminate.clear()
		self._thread.start()
		return True

	# profile_switch is helper telling plugins whether the stop is due to profile switch
	def stop(self, profile_switch = False):
		if not self.is_running():
			return False
		log.info("stopping tunning")
		if profile_switch:
			self._terminate_profile_switch.set()
		self._terminate.set()
		self._thread.join()
		self._thread = None

		return True
