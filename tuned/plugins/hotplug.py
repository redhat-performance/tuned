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
		self._hardware_events_init()

	def cleanup(self):
		super(Plugin, self).cleanup()
		self._hardware_events_cleanup()

	def _hardware_events_init(self):
		raise NotImplementedError()

	def _hardware_events_cleanup(self):
		raise NotImplementedError()

	def _hardware_events_callback(self, event, device):
		if event == "add":
			log.info("device '%s' added" % device.sys_name)
			self._add_device(device)
		elif event == "remove":
			log.info("device '%s' removed" % device.sys_name)
			self._remove_device(device)

	def _add_device(self, device):
		device_name = device.sys_name
		if device_name in (self._assigned_devices | self._free_devices):
			return

		for instance_name, instance in list(self._instances.items()):
			if len(self._get_matching_devices(instance, [device_name])) == 1:
				log.info("instance %s: adding new device %s" % (instance_name, device_name))
				self._assigned_devices.add(device_name)
				instance.devices.add(device_name)
				self._call_device_script(instance, instance.script_pre, "apply", [device_name])
				self._added_device_apply_tuning(instance, device_name)
				self._call_device_script(instance, instance.script_post, "apply", [device_name])
				break
		else:
			log.debug("no instance wants %s" % device_name)
			self._free_devices.add(device_name)

	def _remove_device(self, device):
		device_name = device.sys_name
		if device_name not in (self._assigned_devices | self._free_devices):
			return

		for instance in list(self._instances.values()):
			if device_name in instance.devices:
				self._call_device_script(instance, instance.script_post, "unapply", [device_name])
				self._removed_device_unapply_tuning(instance, device_name)
				self._call_device_script(instance, instance.script_pre, "unapply", [device_name])
				instance.devices.remove(device_name)
				instance.active = len(instance.devices) > 0
				self._assigned_devices.remove(device_name)
				break
		else:
			self._free_devices.remove(device_name)

	def _added_device_apply_tuning(self, instance, device_name):
		self._execute_all_device_commands(instance, [device_name])
		if instance.has_dynamic_tuning and self._global_cfg.get(consts.CFG_DYNAMIC_TUNING, consts.CFG_DEF_DYNAMIC_TUNING):
			self._instance_apply_dynamic(instance, device_name)

	def _removed_device_unapply_tuning(self, instance, device_name):
		if instance.has_dynamic_tuning and self._global_cfg.get(consts.CFG_DYNAMIC_TUNING, consts.CFG_DEF_DYNAMIC_TUNING):
			self._instance_unapply_dynamic(instance, device_name)
		self._cleanup_all_device_commands(instance, [device_name])
