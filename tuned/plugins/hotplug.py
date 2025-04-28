from . import base
import tuned.consts as consts
import tuned.logs

log = tuned.logs.get()

class Plugin(base.Plugin):
	"""
	Base class for plugins with device hotpluging support.
	"""

	def __init__(self, *args, **kwargs):
		super(Plugin, self).__init__(*args, **kwargs)

	def cleanup(self):
		self._hardware_events_cleanup()
		super(Plugin, self).cleanup()

	def _hardware_events_init(self):
		pass

	def _hardware_events_cleanup(self):
		pass

	def _init_devices(self):
		self._hardware_events_init()

	def _hardware_events_callback(self, event, device):
		if event == "add":
			log.info("device '%s', add event" % device.sys_name)
			self._add_device(device.sys_name)
		elif event == "remove":
			log.info("device '%s', remove event" % device.sys_name)
			self._remove_device(device.sys_name)
		elif event == "move":
			log.info("device: '%s', rename event, reported new name" % device.sys_name)
			self._move_device(device.sys_name)

	def _add_device_process(self, instance, device_name):
		log.info("instance %s: adding new device %s" % (instance.name, device_name))
		self._assigned_devices.add(device_name)
		self._call_device_script(instance, instance.script_pre, "apply", [device_name])
		self._added_device_apply_tuning(instance, device_name)
		self._call_device_script(instance, instance.script_post, "apply", [device_name])
		instance.processed_devices.add(device_name)

	def _add_device(self, device_name):
		if device_name in (self._assigned_devices | self._free_devices):
			log.debug("device: '%s' already exists, ignoring" % device_name)
			return

		for instance_name, instance in list(self._instances.items()):
			if len(self._get_matching_devices(instance, [device_name])) == 1:
				self._add_device_process(instance, device_name)
				break
		else:
			log.debug("no instance wants %s" % device_name)
			self._free_devices.add(device_name)

	def _add_devices_nocheck(self, instance, device_names):
		"""
		Add devices specified by the set to the instance, no check is performed.
		"""
		for dev in device_names:
			self._add_device_process(instance, dev)
		# This can be a bit racy (we can overcount),
		# but it shouldn't affect the boolean result
		instance.active = len(instance.processed_devices) \
				+ len(instance.assigned_devices) > 0

	def _remove_device_process(self, instance, device_name):
		if device_name in instance.processed_devices:
			self._call_device_script(instance, instance.script_post, "unapply", [device_name])
			self._removed_device_unapply_tuning(instance, device_name)
			self._call_device_script(instance, instance.script_pre, "unapply", [device_name])
			instance.processed_devices.remove(device_name)
			# This can be a bit racy (we can overcount),
			# but it shouldn't affect the boolean result
			instance.active = len(instance.processed_devices) \
					+ len(instance.assigned_devices) > 0
			self._assigned_devices.remove(device_name)
			return True
		return False

	def _move_device(self, device_name):
		"""Rename device in the instance, this probably applies only
		to network interfaces. The udev device environment is
		mostly unchanged (except the name) and the old device name
		isn't announced, thus the rename functionality is plugin
		dependant and has to be implemented in the child plugin class.

		Parameters:
		device_name -- new name of the device

		"""
		pass

	def _remove_device(self, device_name):
		"""Remove device from the instance

		Parameters:
		device_name -- name of the device

		"""
		if device_name not in (self._assigned_devices | self._free_devices):
			log.debug("device: '%s' doesn't exist, ignoring" % device_name)
			return

		for instance in list(self._instances.values()):
			if self._remove_device_process(instance, device_name):
				break
		else:
			try:
				self._free_devices.remove(device_name)
			except KeyError:
				log.debug("device: '%s' isn't initialized, not removing it" % device_name)

	def _remove_devices_nocheck(self, instance, device_names):
		"""
		Remove devices specified by the set from the instance, no check is performed.
		"""
		for dev in device_names:
			self._remove_device_process(instance, dev)

	def _added_device_apply_tuning(self, instance, device_name):
		self._execute_all_device_commands(instance, [device_name])
		if instance.has_dynamic_tuning and self._global_cfg.get(consts.CFG_DYNAMIC_TUNING, consts.CFG_DEF_DYNAMIC_TUNING):
			self._instance_apply_dynamic(instance, device_name)

	def _removed_device_unapply_tuning(self, instance, device_name):
		if instance.has_dynamic_tuning and self._global_cfg.get(consts.CFG_DYNAMIC_TUNING, consts.CFG_DEF_DYNAMIC_TUNING):
			self._instance_unapply_dynamic(instance, device_name)
		self._cleanup_all_device_commands(instance, [device_name], remove = True)
