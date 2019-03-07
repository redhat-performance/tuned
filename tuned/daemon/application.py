from tuned import storage, units, monitors, plugins, profiles, exports, hardware
from tuned.exceptions import TunedException
import tuned.logs
from . import controller
from . import daemon
import signal
import os
import sys
import select
import struct
import tuned.consts as consts
from tuned.utils.global_config import GlobalConfig

log = tuned.logs.get()

__all__ = ["Application"]

class Application(object):
	def __init__(self, profile_name = None, config = None):
		self._dbus_exporter = None

		storage_provider = storage.PickleProvider()
		storage_factory = storage.Factory(storage_provider)

		self.config = GlobalConfig() if config is None else config
		if self.config.get_bool(consts.CFG_DYNAMIC_TUNING):
			log.info("dynamic tuning is enabled (can be overridden in plugins)")
		else:
			log.info("dynamic tuning is globally disabled")

		monitors_repository = monitors.Repository()
		udev_buffer_size = self.config.get_size("udev_buffer_size", consts.CFG_DEF_UDEV_BUFFER_SIZE)
		hardware_inventory = hardware.Inventory(buffer_size=udev_buffer_size)
		device_matcher = hardware.DeviceMatcher()
		device_matcher_udev = hardware.DeviceMatcherUdev()
		plugin_instance_factory = plugins.instance.Factory()
		self.variables = profiles.variables.Variables()

		plugins_repository = plugins.Repository(monitors_repository, storage_factory, hardware_inventory,\
			device_matcher, device_matcher_udev, plugin_instance_factory, self.config, self.variables)
		def_instance_priority = int(self.config.get(consts.CFG_DEFAULT_INSTANCE_PRIORITY, consts.CFG_DEF_DEFAULT_INSTANCE_PRIORITY))
		unit_manager = units.Manager(
				plugins_repository, monitors_repository,
				def_instance_priority, hardware_inventory)

		profile_factory = profiles.Factory()
		profile_merger = profiles.Merger()
		profile_locator = profiles.Locator(consts.LOAD_DIRECTORIES)
		profile_loader = profiles.Loader(profile_locator, profile_factory, profile_merger, self.config, self.variables)

		self._daemon = daemon.Daemon(unit_manager, profile_loader, profile_name, self.config, self)
		self._controller = controller.Controller(self._daemon, self.config)

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

		try:
			val = struct.unpack("?", response)[0]
		except struct.error:
			raise TunedException("Cannot daemonize, invalid response from child process received.")
		if val != True:
			raise TunedException("Cannot daemonize, child process reports failure.")

	def write_pid_file(self, pid_file = consts.PID_FILE):
		self._pid_file = pid_file
		self._delete_pid_file()
		try:
			dir_name = os.path.dirname(self._pid_file)
			if not os.path.exists(dir_name):
				os.makedirs(dir_name)

			with os.fdopen(os.open(self._pid_file, os.O_CREAT|os.O_TRUNC|os.O_WRONLY , 0o644), "w") as f:
				f.write("%d" % os.getpid())
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
			val = struct.pack("?", False)
			os.write(child_out_fd, val)
			os.close(child_out_fd)
			raise TunedException("Cannot daemonize, second fork() failed.")

		fd = open("/dev/null", "w+")
		os.dup2(fd.fileno(), sys.stdin.fileno())
		os.dup2(fd.fileno(), sys.stdout.fileno())
		os.dup2(fd.fileno(), sys.stderr.fileno())

		self.write_pid_file(pid_file)

		log.debug("successfully daemonized")
		val = struct.pack("?", True)
		os.write(child_out_fd, val)
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

	@property
	def daemon(self):
		return self._daemon

	@property
	def controller(self):
		return self._controller

	def run(self, daemon):
		# override global config if ran from command line with daemon option (-d)
		if daemon:
			self.config.set(consts.CFG_DAEMON, True)
		if not self.config.get_bool(consts.CFG_DAEMON, consts.CFG_DEF_DAEMON):
			log.warn("Using one shot no deamon mode, most of the functionality will be not available, it can be changed in global config")
		result = self._controller.run()
		if self.config.get_bool(consts.CFG_DAEMON, consts.CFG_DEF_DAEMON):
			exports.stop()

		if self._pid_file is not None:
			self._delete_pid_file()

		return result
