from tuned import storage, units, monitors, plugins, profiles, exports, hardware
from tuned.exceptions import TunedException
from configobj import ConfigObj, ConfigObjError
from validate import Validator
import tuned.logs
import controller
import daemon
import signal
import os
import sys
import select
import tuned.consts as consts

log = tuned.logs.get()

__all__ = ["Application"]

global_config_spec = 	["dynamic_tuning = boolean(default=%s)" % consts.CFG_DEF_DYNAMIC_TUNING,
			"sleep_interval = integer(default=%s)" % consts.CFG_DEF_SLEEP_INTERVAL,
			"update_interval = integer(default=%s)" % consts.CFG_DEF_UPDATE_INTERVAL]

class Application(object):
	def __init__(self, profile_name=None):
		storage_provider = storage.PickleProvider()
		storage_factory = storage.Factory(storage_provider)

		monitors_repository = monitors.Repository()
		hardware_inventory = hardware.Inventory()
		device_matcher = hardware.DeviceMatcher()
		plugin_instance_factory = plugins.instance.Factory()
		self.variables = profiles.variables.Variables()

		self.config = self._load_global_config()
		if self.config.get("dynamic_tuning"):
			log.info("dynamic tuning is enabled (can be overriden in plugins)")
		else:
			log.info("dynamic tuning is globally disabled")

		plugins_repository = plugins.Repository(monitors_repository, storage_factory, hardware_inventory, device_matcher, plugin_instance_factory, self.config, self.variables)
		unit_manager = units.Manager(plugins_repository, monitors_repository)

		profile_factory = profiles.Factory()
		profile_merger = profiles.Merger()
		profile_locator = profiles.Locator(consts.LOAD_DIRECTORIES)
		profile_loader = profiles.Loader(profile_locator, profile_factory, profile_merger, self.variables)


		self._daemon = daemon.Daemon(unit_manager, profile_loader, profile_name, self.config)
		self._controller = controller.Controller(self._daemon)

		self._dbus_exporter = None
		self._init_signals()

		self._pid_file = None

	def _handle_signal(self, signal_number, handler):
		def handler_wrapper(_signal_number, _frame):
			if signal_number == _signal_number:
				handler()
		signal.signal(signal_number, handler_wrapper)

	def _init_signals(self):
		self._handle_signal(signal.SIGHUP, self._controller.reload)
		self._handle_signal(signal.SIGINT, self._controller.terminate)
		self._handle_signal(signal.SIGTERM, self._controller.terminate)

	def attach_to_dbus(self, bus_name, object_name, interface_name):
		if self._dbus_exporter is not None:
			raise TunedException("DBus interface is already initialized.")

		self._dbus_exporter = exports.dbus.DBusExporter(bus_name, interface_name, object_name)
		exports.register_exporter(self._dbus_exporter)
		exports.register_object(self._controller)

	def _daemonize_parent(self, parent_in_fd, child_out_fd):
		"""
		Wait till the child signalizes that the initialization is complete by writing
		some uninteresting data into the pipe.
		"""
		os.close(child_out_fd)
		(read_ready, drop, drop) = select.select([parent_in_fd], [], [], consts.DAEMONIZE_PARENT_TIMEOUT)

		if len(read_ready) != 1:
			os.close(parent_in_fd)
			raise TunedException("Cannot daemonize, timeout when waiting for the child process.")

		response = os.read(parent_in_fd, 8)
		os.close(parent_in_fd)

		if len(response) == 0:
			raise TunedException("Cannot daemonize, no response from child process received.")

		if response != ("%c" % True):
			raise TunedException("Cannot daemonize, child process reports failure.")

	def write_pid_file(self, pid_file = consts.PID_FILE):
		self._pid_file = pid_file
		self._delete_pid_file()
		try:
			dir_name = os.path.dirname(self._pid_file)
			if not os.path.exists(dir_name):
				os.makedirs(dir_name)

			fd = os.open(self._pid_file, os.O_CREAT|os.O_TRUNC|os.O_WRONLY , 0644)
			os.write(fd, "%d" % os.getpid())
			os.close(fd)
		except (OSError,IOError) as error:
			log.critical("cannot write the PID to %s: %s" % (self._pid_file, str(error)))

	def _delete_pid_file(self):
		if os.path.exists(self._pid_file):
			try:
				os.unlink(self._pid_file)
			except OSError as error:
				log.warning("cannot remove existing PID file %s, %s" % (self._pid_file, str(error)))

	def _daemonize_child(self, pid_file, parent_in_fd, child_out_fd):
		"""
		Finishes daemonizing process, writes a PID file and signalizes to the parent
		that the initialization is complete.
		"""
		os.close(parent_in_fd)

		os.chdir("/")
		os.setsid()
		os.umask(0)

		try:
			pid = os.fork()
			if pid > 0:
				sys.exit(0)
		except OSError as error:
			log.critical("cannot daemonize, fork() error: %s" % str(error))
			os.write(child_out_fd, "%c" % False)
			os.close(child_out_fd)
			raise TunedException("Cannot daemonize, second fork() failed.")

		si = file("/dev/null", "r")
		so = file("/dev/null", "a+")
		se = file("/dev/null", "a+", 0)
		os.dup2(si.fileno(), sys.stdin.fileno())
		os.dup2(so.fileno(), sys.stdout.fileno())
		os.dup2(se.fileno(), sys.stderr.fileno())

		self.write_pid_file(pid_file)

		log.debug("successfully daemonized")
		os.write(child_out_fd, "%c" % True)
		os.close(child_out_fd)

	def daemonize(self, pid_file = consts.PID_FILE):
		"""
		Daemonizes the application. In case of failure, TunedException is raised
		in the parent process. If the operation is successfull, the main process
		is terminated and only child process returns from this method.
		"""
		parent_child_fds = os.pipe()
		try:
			child_pid = os.fork()
		except OSError as error:
			os.close(parent_child_fds[0])
			os.close(parent_child_fds[1])
			raise TunedException("Cannot daemonize, fork() failed.")

		try:
			if child_pid > 0:
				self._daemonize_parent(*parent_child_fds)
				sys.exit(0)
			else:
				self._daemonize_child(pid_file, *parent_child_fds)
		except:
			# pass exceptions only into parent process
			if child_pid > 0:
				raise
			else:
				sys.exit(1)

	def _load_global_config(self, file_name = consts.GLOBAL_CONFIG_FILE):
		"""
		Loads global configuration file.
		"""
		log.debug("reading and parsing global configuration file '%s'" % consts.GLOBAL_CONFIG_FILE)
		try:
			config = ConfigObj(file_name, configspec=global_config_spec, raise_errors = True, file_error = True)
		except IOError as e:
			raise TunedException("Global tuned configuration file '%s' not found." % file_name)
		except ConfigObjError as e:
			raise TunedException("Error parsing global tuned configuration file '%s'." % file_name)
		vdt = Validator()
		if (not config.validate(vdt, copy=True)):
			raise TunedException("Global tuned configuration file '%s' is not valid." % file_name)
		return config

	@property
	def daemon(self):
		return self._daemon

	@property
	def controller(self):
		return self._controller

	def run(self):
		exports.start()
		result = self._controller.run()
		exports.stop()

		if self._pid_file is not None:
			self._delete_pid_file()

		return result
