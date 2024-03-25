from . import hotplug
from .decorators import *
import tuned.consts as consts
import tuned.logs

import errno
import os

log = tuned.logs.get()

class IrqInfo(object):
	def __init__(self, irq):
		self.irq = irq
		self.device = "irq%s" % irq
		self.unchangeable = False
		self.original_affinity = None

class IrqPlugin(hotplug.Plugin):
	r"""
	`irq`::

	Allows tuning of IRQ affinities, and thus re-implements functionality
	already present in the `scheduler` plugin. However, this plugin offers
	more flexibility, as it allows tuning of individual interrupts with
	different affinities. When using the `irq` plugin, make sure to disable
	IRQ processing in the `scheduler` plugin by setting its option
	[option]`irq_process=false`.
	The plugin handles individual IRQs as `devices`, and multiple plugin
	instances can be defined, each addressing different devices/irqs.
	===
	The option [option]`affinity` controls the IRQ affinity to be set.
	===
	The option [option]`default_affinity` controls the values written to
	`/proc/irq/default_smp_affinity`, which applies to all non-active IRQs.
	+
	The following values are supported:
	+
	--
	`calc`::
	Content of `/proc/irq/default_smp_affinity` will be calculated
	from the `isolated_cores` parameter. Non-isolated cores
	are calculated as an inversion of the `isolated_cores`. Then
	the intersection of the non-isolated cores and the previous
	content of `/proc/irq/default_smp_affinity` is written to
	`/proc/irq/default_smp_affinity`. If the intersection is
	an empty set, then just the non-isolated cores are written to
	`/proc/irq/default_smp_affinity`. This behavior is the default if
	the parameter `default_irq_smp_affinity` is omitted.
	`ignore`::
	*TuneD* will not touch `/proc/irq/default_smp_affinity`.
	explicit cpulist::
	The cpulist (such as 1,3-4) is unpacked and written directly to
	`/proc/irq/default_smp_affinity`.
	--
	.Example moving all IRQs to CPU0, except irq16, which is directed to CPU2
	====
	----
	[irq]
	affinity=0
	default_affinity=0
	[irq16]
	type=irq
	devices=irq16
	affinity=2
	----
	====
	"""

	def __init__(self, monitor_repository, storage_factory, hardware_inventory, device_matcher, device_matcher_udev, plugin_instance_factory, global_cfg, variables):
		super(IrqPlugin, self).__init__(monitor_repository, storage_factory, hardware_inventory, device_matcher, device_matcher_udev, plugin_instance_factory, global_cfg, variables)
		self._irqs = {}
		self._irqdefault = IrqInfo("default")

	#
	# plugin-level methods: devices and plugin options
	#
	def _init_devices(self):
		"""Read /proc/irq to collect devices
		"""
		self._devices_supported = True
		self._free_devices = set()
		self._assigned_devices = set()
		for i in os.listdir("/proc/irq"):
			p = os.path.join("/proc/irq", i)
			if os.path.isdir(p) and i.isdigit():
				info = IrqInfo(i)
				self._irqs[int(i)] = info
				self._free_devices.add(info.device)

	@classmethod
	def _get_config_options(cls):
		return {
			"affinity": "",
			"default_affinity": None,
		}

	#
	# instance-level methods: implement the Instance interface
	#
	def _instance_init(self, instance):
		instance._has_static_tuning = True
		instance._has_dynamic_tuning = False
		instance._is_main_instance = instance.name == instance.plugin.name

		affinity = instance.options.get("affinity")
		affinity_list = self._cmd.cpulist_unpack(affinity)
		instance._affinity = set(affinity_list)
		if len(affinity_list) == 0:
			log.info("Instance '%s' has no affinity. Deactivating." % instance.name)
			instance._active = False

		# only the main instace of the plugin can set the default affinity
		default_affinity = instance.options.get("default_affinity", None)
		if instance._is_main_instance:
			if default_affinity is None:
				instance._default_affinity = "calc"
			elif default_affinity in ["calc", "ignore"]:
				instance._default_affinity = "ignore"
			else:
				instance._default_affinity = set(self._cmd.cpulist_unpack(default_affinity))
		else:
			if default_affinity is not None:
				log.info("'default_affinity' from non-main IRQ plugin instance '%s' will be ignored." % instance.name)

	def _instance_cleanup(self, instance):
		pass

	def _instance_apply_static(self, instance):
		super(IrqPlugin, self)._instance_apply_static(instance)
		if instance._is_main_instance:
			prev_affinity = self._get_irq_affinity("default")
			if instance._default_affinity == "calc":
				new_affinity = prev_affinity & instance._affinity or instance._affinity
				self._apply_irq_affinity(self._irqdefault, new_affinity)
			elif instance._default_affinity != "ignore":
				self._apply_irq_affinity(self._irqdefault, instance._default_affinity)

	def _instance_unapply_static(self, instance, rollback):
		super(IrqPlugin, self)._instance_unapply_static(instance, rollback)
		if instance._is_main_instance:
			if instance._default_affinity != "ignore":
				self._restore_irq_affinity(self._irqdefault)

	def _instance_verify_static(self, instance, ignore_missing, devices):
		log.debug("Verifying IRQ affinities (%s)" % instance.name)
		ret = super(IrqPlugin, self)._instance_verify_static(instance, ignore_missing, devices)
		if instance._is_main_instance:
			prev_affinity = self._irqdefault.original_affinity
			if instance._default_affinity == "calc":
				desired_affinity = prev_affinity & instance._affinity or instance._affinity
				ret &= self._verify_irq_affinity(self._irqdefault, desired_affinity)
			elif instance._default_affinity != "ignore":
				ret &= self._verify_irq_affinity(self._irqdefault, instance._default_affinity)
		return ret

	#
	# "low-level" methods to get/set irq affinities
	#
	def _get_irq_affinity(self, irq):
		"""Get current IRQ affinity from the kernel

		Args:
			irq (str): IRQ number (as string) or "default"

		Returns:
			affinity (set): set of all CPUs that belong to the IRQ affinity mask
		"""
		filename = "/proc/irq/default_smp_affinity" if irq == "default" else "/proc/irq/%s/smp_affinity" % irq
		with open(filename, "r") as f:
			affinity_hex = f.readline().strip()
		return set(self._cmd.hex2cpulist(affinity_hex))

	def _set_irq_affinity(self, irq, affinity, restoring):
		"""Set IRQ affinity in the kernel

		Args:
			irq (str): IRQ number (as string) or "default"
			affinity (set): affinity mask as set of CPUs
			restoring (bool): are we rolling back a previous change?

		Returns:
			status (int):  0 on success, -2 if changing the affinity is not
				supported, -1 if some other error occurs
		"""
		try:
			affinity_hex = self._cmd.cpulist2hex(list(affinity))
			log.debug("Setting SMP affinity of IRQ %s to '%s'"
					% (irq, affinity_hex))
			filename = "/proc/irq/default_smp_affinity" if irq == "default" else "/proc/irq/%s/smp_affinity" % irq
			with open(filename, "w") as f:
				f.write(affinity_hex)
			return 0
		except (OSError, IOError) as e:
			# EIO is returned by
			# kernel/irq/proc.c:write_irq_affinity() if changing
			# the affinity is not supported
			# (at least on kernels 3.10 and 4.18)
			if hasattr(e, "errno") and e.errno == errno.EIO \
					and not restoring:
				log.debug("Setting SMP affinity of IRQ %s is not supported"
						% irq)
				return -2
			else:
				log.error("Failed to set SMP affinity of IRQ %s to '%s': %s"
						% (irq, affinity_hex, e))
				return -1

	#
	# "high-level" methods: apply tuning while saving original affinities
	#
	def _apply_irq_affinity(self, irqinfo, affinity):
		"""Apply IRQ affinity tuning

		Args:
			irqinfo (IrqInfo): IRQ that should be tuned
			affinity (set): desired affinity
		"""
		original = self._get_irq_affinity(irqinfo.irq)
		if irqinfo.unchangeable or affinity == original:
			return
		res = self._set_irq_affinity(irqinfo.irq, affinity, False)
		if res == 0:
			if irqinfo.original_affinity is None:
				irqinfo.original_affinity = original
		elif res == -2:
			irqinfo.unchangeable = True

	def _restore_irq_affinity(self, irqinfo):
		"""Restore IRQ affinity

		Args:
			irqinfo (IrqInfo): IRQ that should be restored
		"""
		if irqinfo.unchangeable or irqinfo.original_affinity is None:
			return
		self._set_irq_affinity(irqinfo.irq, irqinfo.original_affinity, True)
		irqinfo.original_affinity = None

	def _verify_irq_affinity(self, irqinfo, affinity):
		"""Verify IRQ affinity tuning

		Args:
			irqinfo (IrqInfo): IRQ that should be verified
			affinity (set): desired affinity

		Returns:
			status (bool): True if verification successful, False otherwise
		"""
		if irqinfo.unchangeable:
			return True
		affinity_description = "IRQ %s affinity" % irqinfo.irq
		desired_affinity_string = self._cmd.cpulist2string(self._cmd.cpulist_pack(list(affinity)))
		current_affinity_string = self._cmd.cpulist2string(self._cmd.cpulist_pack(list(self._get_irq_affinity(irqinfo.irq))))
		if current_affinity_string == desired_affinity_string:
			log.info(consts.STR_VERIFY_PROFILE_VALUE_OK
					% (affinity_description, current_affinity_string))
			return True
		else:
			log.error(consts.STR_VERIFY_PROFILE_DEVICE_VALUE_FAIL
					% (affinity_description, current_affinity_string, desired_affinity_string))
			return False

	#
	# command definitions: entry to device-specific tuning
	#
	@command_custom("affinity", per_device=True)
	def _affinity(self, start, value, device, verify, ignore_missing):
		irq = int(device[len("irq"):])
		if irq not in self._irqs:
			log.error("Unknown device: %s" % device)
			return None
		irqinfo = self._irqs[irq]
		if verify:
			affinity = set(self._cmd.cpulist_unpack(value))
			return self._verify_irq_affinity(irqinfo, affinity)
		if start:
			affinity = set(self._cmd.cpulist_unpack(value))
			return self._apply_irq_affinity(irqinfo, affinity)
		else:
			return self._restore_irq_affinity(irqinfo)
