import os
import errno
import threading
import tuned.logs
from tuned.exceptions import TunedException
from tuned.profiles.exceptions import InvalidProfileException
import tuned.consts as consts
from tuned.utils.commands import commands
from tuned import exports

log = tuned.logs.get()


class Daemon(object):
	def __init__(self, unit_manager, profile_loader, profile_name=None, config=None, application=None):
		log.debug("initializing daemon")
		self._daemon = consts.CFG_DEF_DAEMON
		self._sleep_interval = int(consts.CFG_DEF_SLEEP_INTERVAL)
		self._update_interval = int(consts.CFG_DEF_UPDATE_INTERVAL)
		self._dynamic_tuning = consts.CFG_DEF_DYNAMIC_TUNING
		self._recommend_command = True
		if config is not None:
			self._daemon = config.get_bool(consts.CFG_DAEMON, consts.CFG_DEF_DAEMON)
			self._sleep_interval = int(config.get(consts.CFG_SLEEP_INTERVAL, consts.CFG_DEF_SLEEP_INTERVAL))
			self._update_interval = int(config.get(consts.CFG_UPDATE_INTERVAL, consts.CFG_DEF_UPDATE_INTERVAL))
			self._dynamic_tuning = config.get_bool(consts.CFG_DYNAMIC_TUNING, consts.CFG_DEF_DYNAMIC_TUNING)
			self._recommend_command = config.get_bool(consts.CFG_RECOMMEND_COMMAND, consts.CFG_DEF_RECOMMEND_COMMAND)
		self._application = application
		if self._sleep_interval <= 0:
			self._sleep_interval = int(consts.CFG_DEF_SLEEP_INTERVAL)
		if self._update_interval == 0:
			self._dynamic_tuning = False
		elif self._update_interval < self._sleep_interval:
			self._update_interval = self._sleep_interval
		self._sleep_cycles = self._update_interval // self._sleep_interval
		log.info("using sleep interval of %d second(s)" % self._sleep_interval)
		if self._dynamic_tuning:
			log.info("dynamic tuning is enabled (can be overridden by plugins)")
			log.info("using update interval of %d second(s) (%d times of the sleep interval)" % (self._sleep_cycles * self._sleep_interval, self._sleep_cycles))

		self._unit_manager = unit_manager
		self._profile_loader = profile_loader
		self._init_threads()
		self._cmd = commands()
		try:
			self._init_profile(profile_name)
		except TunedException as e:
			log.error("Cannot set initial profile. No tunings will be enabled: %s" % e)

	def _init_threads(self):
		self._thread = None
		self._terminate = threading.Event()
		# Flag which is set if terminating due to profile_switch
		self._terminate_profile_switch = threading.Event()
		# Flag which is set if there is no operation in progress
		self._not_used = threading.Event()
		self._not_used.set()
		self._profile_applied = threading.Event()

	def _init_profile(self, profile_name):
		manual = True
		if profile_name is None:
			(profile_name, manual) = self._get_startup_profile()

		self._profile = None
		self._manual = None
		self.set_profile(profile_name, manual)

	def set_profile(self, profile_name, manual, save_instantly=False):
		if self.is_running():
			raise TunedException(self._notify_profile_changed(profile_name, False, "Cannot set profile while the daemon is running."))

		if profile_name == "" or profile_name is None:
			self._profile = None
			self._manual = None
		elif profile_name not in self.profile_loader.profile_locator.get_known_names():
			raise TunedException(self._notify_profile_changed(profile_name, False, "Requested profile '%s' doesn't exist." % profile_name))
		else:
			try:
				self._profile = self._profile_loader.load(profile_name)
				self._manual = manual
			except InvalidProfileException as e:
				raise TunedException(self._notify_profile_changed(profile_name, False, "Cannot load profile '%s': %s" % (profile_name, e)))

		if save_instantly:
			if profile_name is None:
				profile_name = ""
			self._save_active_profile(profile_name, manual)

	@property
	def profile(self):
		return self._profile

	@property
	def manual(self):
		# manual == None means /etc/tuned/active_profile is empty -> automatic mode
		return self._manual == True or self._manual is None

	@property
	def profile_loader(self):
		return self._profile_loader

	# send notification when profile is changed (everything is setup) or if error occured
	# result: True - OK, False - error occured
	def _notify_profile_changed(self, profile_name, result, errstr):
		if self._application is not None and self._application._dbus_exporter is not None:
			self._application._dbus_exporter.send_signal(consts.DBUS_SIGNAL_PROFILE_CHANGED, profile_name, result, errstr)
		return errstr

	def _thread_code(self):
		if self._profile is None:
			raise TunedException("Cannot start the daemon without setting a profile.")

		self._unit_manager.create(self._profile.units)
		self._save_active_profile(self._profile.name, self._manual)
		self._unit_manager.start_tuning()
		self._profile_applied.set()
		log.info("static tuning from profile '%s' applied" % self._profile.name)
		if not exports.wait_for_exports_running(0):
			log.info("Waiting for exports to start.")
			i = 0
			res = False
			while not res and i < 120:
				res = exports.wait_for_exports_running(0.5)
				i += 1
			if res:
				log.info("Exports started")
				self._notify_profile_changed(self._profile.name, True, "OK")
			else:
				log.critical("Timed out waiting for exports, stopping daemon.")
				self._terminate.set()
		else:
			self._notify_profile_changed(self._profile.name, True, "OK")

		if self._daemon:
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

		self._profile_applied.clear()

		# wait for others to complete their tasks, use timeout 3 x sleep_interval to prevent
		# deadlocks
		i = 0
		while not self._cmd.wait(self._not_used, self._sleep_interval) and i < 3:
			i += 1

		# if terminating due to profile switch
		if self._terminate_profile_switch.is_set():
			full_rollback = True
		else:
			# with systemd it detects system shutdown and in such case it doesn't perform
			# full cleanup, if not shutting down it means that Tuned was explicitly
			# stopped by user and in such case do full cleanup, without systemd never
			# do full cleanup
			full_rollback = False
			retcode, out = self._cmd.execute(["systemctl", "is-system-running"], no_errors = [0])
			if retcode >= 0:
				if out[:8] == "stopping":
					log.info("terminating Tuned due to system shutdown / reboot")
				else:
					log.info("terminating Tuned, rolling back all changes")
					full_rollback = True
		if self._daemon:
			self._unit_manager.stop_tuning(full_rollback)
		self._unit_manager.destroy_all()

	def _save_active_profile(self, profile_name, manual):
		try:
			with open(consts.ACTIVE_PROFILE_FILE, "w") as f:
				if len(profile_name) > 0:
					f.write(profile_name + "\n")
					if manual:
						f.write(consts.ACTIVE_PROFILE_MANUAL + "\n")
					else:
						f.write(consts.ACTIVE_PROFILE_AUTO + "\n")
		except (OSError,IOError) as e:
			log.error("Cannot write active profile into %s: %s" % (consts.ACTIVE_PROFILE_FILE, str(e)))

	def _set_recommended_profile(self):
		log.info("no profile preset, checking what is recommended for your configuration")
		profile = self._cmd.recommend_profile(hardcoded = not self._recommend_command)
		log.info("using '%s' profile and setting it as active" % profile)
		self._save_active_profile(profile, False)
		return profile

	def _get_startup_profile(self):
		manual = False
		try:
			with open(consts.ACTIVE_PROFILE_FILE, "r") as f:
				content = f.read().strip()
				if content == "":
					profile = self._set_recommended_profile()
				else:
					arr = content.split('\n')
					if len(arr) > 2 or (len(arr) == 2 and arr[1] != consts.ACTIVE_PROFILE_AUTO and arr[1] != consts.ACTIVE_PROFILE_MANUAL):
						profile = self._set_recommended_profile()
						log.error("cannot read active profile from '%s': bad format. Falling back to '%s' profile."
								% consts.ACTIVE_PROFILE_FILE, profile)
					else:
						profile = arr[0]
						if len(arr) == 2:
							manual = arr[1] == consts.ACTIVE_PROFILE_MANUAL
							if not manual:
								profile = self._set_recommended_profile()
						else:
							# The file has only one line - generated by previous Tuned version.
							# Treat the profile as manually set.
							manual = True
				return (profile, manual)
		except IOError as e:
			if e.errno == errno.ENOENT:
				# No such file or directory
				profile = self._set_recommended_profile()
			else:
				profile = consts.DEFAULT_PROFILE
				log.error("error reading active profile from '%s', falling back to '%s' profile" % (consts.ACTIVE_PROFILE_FILE, profile))
			return (profile, manual)
		except (OSError, EOFError) as e:
			log.error("cannot read active profile, falling back to '%s' profile" % consts.DEFAULT_PROFILE)
			return (consts.DEFAULT_PROFILE, manual)

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
		self._not_used.set()
		self._thread = threading.Thread(target=self._thread_code)
		self._terminate_profile_switch.clear()
		self._terminate.clear()
		self._thread.start()
		return True

	def verify_profile(self, ignore_missing):
		if not self.is_running():
			log.error("tuned is not running")
			return False

		if self._profile is None:
			log.error("no profile is set")
			return False

		if not self._profile_applied.is_set():
			log.error("profile is not applied")
			return False

		# using deamon, the main loop mustn't exit before our completion
		self._not_used.clear()
		log.info("verifying profile(s): %s" % self._profile.name)
		ret = self._unit_manager.verify_tuning(ignore_missing)
		# main loop is allowed to exit
		self._not_used.set()
		return ret

	# profile_switch is helper telling plugins whether the stop is due to profile switch
	def stop(self, profile_switch = False):
		if not self.is_running():
			return False
		log.info("stopping tuning")
		if profile_switch:
			self._terminate_profile_switch.set()
		self._terminate.set()
		self._thread.join()
		self._thread = None

		return True

	def wait_for_profile_applied(self, timeout):
		return self._cmd.wait(self._profile_applied, timeout)
