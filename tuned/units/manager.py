import collections
import os
import re
import traceback
import tuned.exceptions
import tuned.logs
import tuned.plugins.exceptions
import tuned.consts as consts
from tuned.utils.global_config import GlobalConfig
from tuned.utils.commands import commands

log = tuned.logs.get()

__all__ = ["Manager"]

class Manager(object):
	"""
	Manager creates plugin instances and keeps a track of them.
	"""

	def __init__(self, plugins_repository, monitors_repository,
			def_instance_priority, hardware_inventory, config = None):
		super(Manager, self).__init__()
		self._plugins_repository = plugins_repository
		self._monitors_repository = monitors_repository
		self._def_instance_priority = def_instance_priority
		self._hardware_inventory = hardware_inventory
		self._instances = []
		self._plugins = []
		self._config = config or GlobalConfig()
		self._cmd = commands()

	@property
	def plugins(self):
		return self._plugins

	@property
	def instances(self):
		return self._instances

	@property
	def plugins_repository(self):
		return self._plugins_repository

	def _unit_matches_cpuinfo(self, unit):
		if unit.cpuinfo_regex is None:
			return True
		cpuinfo_string = self._config.get(consts.CFG_CPUINFO_STRING)
		if cpuinfo_string is None:
			cpuinfo_string = self._cmd.read_file("/proc/cpuinfo")
		return re.search(unit.cpuinfo_regex, cpuinfo_string,
				re.MULTILINE) is not None

	def _unit_matches_uname(self, unit):
		if unit.uname_regex is None:
			return True
		uname_string = self._config.get(consts.CFG_UNAME_STRING)
		if uname_string is None:
			uname_string = " ".join(os.uname())
		return re.search(unit.uname_regex, uname_string,
				re.MULTILINE) is not None

	def create(self, instances_config):
		instance_info_list = []
		for instance_name, instance_info in list(instances_config.items()):
			if not instance_info.enabled:
				log.debug("skipping disabled instance '%s'" % instance_name)
				continue
			if not self._unit_matches_cpuinfo(instance_info):
				log.debug("skipping instance '%s', cpuinfo does not match" % instance_name)
				continue
			if not self._unit_matches_uname(instance_info):
				log.debug("skipping instance '%s', uname does not match" % instance_name)
				continue

			if instance_info.priority is None:
				instance_info.priority = int(self._def_instance_priority)
			else:
				instance_info.priority = int(instance_info.priority)
			instance_info_list.append(instance_info)

		instance_info_list.sort(key=lambda x: x.priority)
		plugins_by_name = collections.OrderedDict()
		for instance_info in instance_info_list:
			plugins_by_name[instance_info.type] = None

		for plugin_name, none in list(plugins_by_name.items()):
			try:
				plugin = self._plugins_repository.create(plugin_name)
				plugins_by_name[plugin_name] = plugin
				self._plugins.append(plugin)
			except tuned.plugins.exceptions.NotSupportedPluginException as e:
				log.info("skipping plugin '%s', not supported on your system: %s" % (plugin_name, e))
				continue
			except Exception as e:
				log.error("failed to initialize plugin %s" % plugin_name)
				log.exception(e)
				continue

		instances = []
		for instance_info in instance_info_list:
			plugin = plugins_by_name[instance_info.type]
			if plugin is None:
				continue
			log.debug("creating '%s' (%s)" % (instance_info.name, instance_info.type))
			new_instance = plugin.create_instance(instance_info.name, instance_info.priority, \
				instance_info.devices, instance_info.devices_udev_regex, \
				instance_info.script_pre, instance_info.script_post, instance_info.options)
			instances.append(new_instance)
		for instance in instances:
			instance.plugin.init_devices()
			instance.plugin.assign_free_devices(instance)
			instance.plugin.initialize_instance(instance)
		# At this point we should be able to start the HW events
		# monitoring/processing thread, without risking race conditions
		self._hardware_inventory.start_processing_events()
		self._instances.extend(instances)

	def _try_call(self, caller, exc_ret, f, *args, **kwargs):
		try:
			return f(*args, **kwargs)
		except Exception as e:
			trace = traceback.format_exc()
			log.error("BUG: Unhandled exception in %s: %s"
					% (caller, str(e)))
			log.error(trace)
			return exc_ret

	def destroy_all(self):
		for instance in self._instances:
			log.debug("destroying instance %s" % instance.name)
			self._try_call("destroy_all", None,
					instance.plugin.destroy_instance,
					instance)
		for plugin in self._plugins:
			log.debug("cleaning plugin '%s'" % plugin.name)
			self._try_call("destroy_all", None, plugin.cleanup)
		self._plugins_repository.plugins.clear()
		del self._plugins[:]
		del self._instances[:]

	def update_monitors(self):
		for monitor in self._monitors_repository.monitors:
			log.debug("updating monitor %s" % monitor)
			self._try_call("update_monitors", None, monitor.update)

	def start_tuning(self):
		for instance in self._instances:
			self._try_call("start_tuning", None,
					instance.apply_tuning)

	def verify_tuning(self, ignore_missing):
		ret = True
		for instance in self._instances:
			res = self._try_call("verify_tuning", False,
					instance.verify_tuning, ignore_missing)
			if res == False:
				ret = False
		return ret

	def update_tuning(self):
		for instance in self._instances:
			self._try_call("update_tuning", None,
					instance.update_tuning)

	# rollback parameter is a helper telling plugins whether soft or full
	# rollback is needed, e.g. for bootloader plugin we need grub.cfg
	# tuning to persist across reboots and restarts of the daemon, so in
	# this case the rollback is usually set to consts.ROLLBACK_SOFT,
	# but we also need to clean it all up when TuneD is disabled or the
	# profile is changed. In this case the rollback is set to
	# consts.ROLLBACK_FULL. In practice it means to remove all temporal
	# or helper files, unpatch third party config files, etc.
	def stop_tuning(self, rollback = consts.ROLLBACK_SOFT):
		self._hardware_inventory.stop_processing_events()
		for instance in reversed(self._instances):
			self._try_call("stop_tuning", None,
					instance.unapply_tuning, rollback)
