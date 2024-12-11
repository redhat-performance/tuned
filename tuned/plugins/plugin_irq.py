from . import hotplug
from .decorators import *
import tuned.consts as consts
import tuned.logs

import errno
import os

log = tuned.logs.get()

# the plugin manages each IRQ as a "device" and keeps a IrqInfo object for it
class IrqInfo(object):
	def __init__(self, irq):
		self.irq = irq
		self.device = "irq%s" % irq
		self.unchangeable = False
		self.original_affinity = None

class IrqPlugin(hotplug.Plugin):
	r"""
	Allows tuning of IRQ affinities, and thus re-implements functionality
	already present in the `scheduler` plugin. However, this plugin offers
	more flexibility, as it allows tuning of individual interrupts with
	different affinities. When using the `irq` plugin, make sure to disable
	IRQ processing in the `scheduler` plugin by setting its option
	[option]`irq_process=false`.

	The plugin handles individual IRQs as devices and multiple plugin
	instances can be defined, each addressing different devices/irqs.
	The device names used by the plugin are `irq<n>`, where `<n>` is the
	IRQ number. The special device `DEFAULT` controls values written to
	`/proc/irq/default_smp_affinity`, which applies to all non-active IRQs.

	The option [option]`affinity` controls the IRQ affinity to be set. It is
	a string in "cpulist" format (such as `1,3-4`). If the configured affinity
	is empty, then the affinity of the respective IRQs is not touched.

	The option [option]`mode` is a string which can either be `set` (default)
	or `intersect`. In `set` mode the [option]`affinity` is always written
	as configured, whereas in `intersect` mode, the new affinity will be
	calculated as the intersection of the current and the configured affinity.
	If that intersection is empty, the configured affinity will be used.

	.Moving all IRQs to CPU0, except irq16, which is directed to CPU2
	====
	----
	[irq_special]
	type=irq
	devices=irq16
	affinity=2

	[irq]
	affinity=0
	----
	====
	"""

	def __init__(self, monitor_repository, storage_factory, hardware_inventory, device_matcher, device_matcher_udev, plugin_instance_factory, global_cfg, variables):
		super(IrqPlugin, self).__init__(monitor_repository, storage_factory, hardware_inventory, device_matcher, device_matcher_udev, plugin_instance_factory, global_cfg, variables)
		self._irqs = {}

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
				self._irqs[i] = info
				self._free_devices.add(info.device)
		# add the virtual device for default_smp_affinity
		default_info = IrqInfo("DEFAULT")
		default_info.device = "DEFAULT"
		self._irqs["DEFAULT"] = default_info
		self._free_devices.add(default_info.device)

	@classmethod
	def _get_config_options(cls):
		return {
			"affinity": "",
			"mode": "set",
		}

	#
	# instance-level methods: implement the Instance interface
	#
	def _instance_init(self, instance):
		instance._has_static_tuning = True
		instance._has_dynamic_tuning = False

		affinity = self._variables.expand(instance.options.get("affinity"))
		affinity_list = self._cmd.cpulist_unpack(affinity)
		if len(affinity.strip()) == 0:
			# empty affinity in profile -> assume it's intentional
			log.info("Instance '%s' configured with empty affinity. Deactivating." % instance.name)
			instance._active = False
		elif len(affinity_list) == 0:
			# non-empty affinity string evaluates to empty list -> assume parse error
			log.error("Instance '%s' with invalid affinity '%s'. Deactivating." % (instance.name, affinity))
			instance._active = False

		mode = self._variables.expand(instance.options.get("mode"))
		if mode not in ["set", "intersect"]:
			log.error("Invalid operating mode '%s' for instance '%s'. Using the default 'set' instead."
					% (mode, instance.name))
			instance.options["mode"] = "set"

	def _instance_cleanup(self, instance):
		pass

	def _instance_apply_static(self, instance):
		log.debug("Applying IRQ affinities (%s)" % instance.name)
		super(IrqPlugin, self)._instance_apply_static(instance)

	def _instance_unapply_static(self, instance, rollback):
		log.debug("Unapplying IRQ affinities (%s)" % instance.name)
		super(IrqPlugin, self)._instance_unapply_static(instance, rollback)

	def _instance_verify_static(self, instance, ignore_missing, devices):
		log.debug("Verifying IRQ affinities (%s)" % instance.name)
		return super(IrqPlugin, self)._instance_verify_static(instance, ignore_missing, devices)

	#
	# "low-level" methods to get/set irq affinities
	#
	def _get_irq_affinity(self, irq):
		"""Get current IRQ affinity from the kernel

		Args:
			irq (str): IRQ number (as string) or "DEFAULT"

		Returns:
			affinity (set): set of all CPUs that belong to the IRQ affinity mask,
				if reading of the affinity fails, an empty set is returned
		"""
		try:
			filename = "/proc/irq/default_smp_affinity" if irq == "DEFAULT" else "/proc/irq/%s/smp_affinity" % irq
			with open(filename, "r") as f:
				affinity_hex = f.readline().strip()
			return set(self._cmd.hex2cpulist(affinity_hex))
		except (OSError, IOError) as e:
			log.debug("Failed to read SMP affinity of IRQ %s: %s" % (irq, e))
			return set()

	def _set_irq_affinity(self, irq, affinity, restoring):
		"""Set IRQ affinity in the kernel

		Args:
			irq (str): IRQ number (as string) or "DEFAULT"
			affinity (set): affinity mask as set of CPUs
			restoring (bool): are we rolling back a previous change?

		Returns:
			status (int):  0 on success, -2 if changing the affinity is not
				supported, -1 if some other error occurs
		"""
		try:
			affinity_hex = self._cmd.cpulist2hex(list(affinity))
			log.debug("Setting SMP affinity of IRQ %s to '%s'" % (irq, affinity_hex))
			filename = "/proc/irq/default_smp_affinity" if irq == "DEFAULT" else "/proc/irq/%s/smp_affinity" % irq
			with open(filename, "w") as f:
				f.write(affinity_hex)
			return 0
		except (OSError, IOError) as e:
			# EIO is returned by
			# kernel/irq/proc.c:write_irq_affinity() if changing
			# the affinity is not supported
			# (at least on kernels 3.10 and 4.18)
			if hasattr(e, "errno") and e.errno == errno.EIO and not restoring:
				log.debug("Setting SMP affinity of IRQ %s is not supported" % irq)
				return -2
			else:
				log.error("Failed to set SMP affinity of IRQ %s to '%s': %s" % (irq, affinity_hex, e))
				return -1

	#
	# "high-level" methods: apply tuning while saving original affinities
	#
	def _apply_irq_affinity(self, irqinfo, affinity, mode):
		"""Apply IRQ affinity tuning

		Args:
			irqinfo (IrqInfo): IRQ that should be tuned
			affinity (set): desired affinity
		"""
		original = self._get_irq_affinity(irqinfo.irq)
		if mode == "intersect":
			# intersection of affinity and original, if that is empty fall back to configured affinity
			affinity = affinity & original or affinity
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

	def _verify_irq_affinity(self, irqinfo, affinity, mode):
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
		desired_affinity = affinity
		desired_affinity_string = self._cmd.cpulist2string(self._cmd.cpulist_pack(list(desired_affinity)))
		current_affinity = self._get_irq_affinity(irqinfo.irq)
		current_affinity_string = self._cmd.cpulist2string(self._cmd.cpulist_pack(list(current_affinity)))
		if mode == "intersect":
			# In intersect mode, we don't use a strict comparison; it's sufficient
			# if the current affinity is a subset of the desired one
			desired_affinity_string = "subset of " + desired_affinity_string
		if ((mode == "intersect" and current_affinity <= desired_affinity) or
					(mode == "set" and current_affinity == desired_affinity)):
			log.info(consts.STR_VERIFY_PROFILE_VALUE_OK
					% (affinity_description, desired_affinity_string))
			return True
		else:
			log.error(consts.STR_VERIFY_PROFILE_VALUE_FAIL
					% (affinity_description, current_affinity_string, desired_affinity_string))
			return False

	#
	# command definitions: entry to device-specific tuning
	#
	@command_custom("mode", per_device=False, priority=-10)
	def _mode(self, enabling, value, verify, ignore_missing):
		if (enabling or verify) and value is not None:
			# Store the operating mode of the current instance in the plugin
			# object, from where it is read by the "affinity" command.
			# This works because instances are processed sequentially by the engine.
			self._mode_val = value

	@command_custom("affinity", per_device=True)
	def _affinity(self, enabling, value, device, verify, ignore_missing):
		irq = "DEFAULT" if device == "DEFAULT" else device[len("irq"):]
		if irq not in self._irqs:
			log.error("Unknown device: %s" % device)
			return None
		irqinfo = self._irqs[irq]
		if verify:
			affinity = set(self._cmd.cpulist_unpack(value))
			return self._verify_irq_affinity(irqinfo, affinity, self._mode_val)
		if enabling:
			affinity = set(self._cmd.cpulist_unpack(value))
			return self._apply_irq_affinity(irqinfo, affinity, self._mode_val)
		else:
			return self._restore_irq_affinity(irqinfo)
