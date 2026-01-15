from . import base
from .decorators import *
import tuned.consts as consts
import tuned.logs

# The scheduler interface in os was introduced in Python 3.3
# To also support earlier versions, we import some logic from plugin_scheduler
from .plugin_scheduler import SchedulerUtils, SchedulerUtilsSchedutils

try:
	import perf
	have_perf = True
except ModuleNotFoundError:
	have_perf = False
import procfs

import errno
import os
import re
import select
import threading
import time

log = tuned.logs.get()

# threads can disappear at any time. in that case, we raise a custom exception
class ThreadNoLongerExists(Exception):
	pass

# another custom exception to signal non-changeability of affinities
class AffinityNotChangeable(Exception):
	pass

# the plugin keeps a KthreadInfo object for each kthread
class KthreadInfo(object):
	def __init__(self, proc):
		self.pid = proc.pid
		self.comm = procfs.process_cmdline(proc)
		self.affinity_changeable = None
		self.sched_orig = None
		self.tuned_affinity = False
		self.tuned_sched = False

	def __str__(self):
		return "%d:%s" % (self.pid, self.comm)

# scheduling options
class SchedOpts(object):
	def __init__(self, policy=None, priority=None, affinity=None):
		self.policy = policy
		self.priority = priority
		self.affinity = affinity

# group.* definitions from the instance options
class GroupCmd(object):
	def __init__(self, name, prio, sched, regex):
		self.name = name
		self.prio = prio
		self.sched = sched
		self.regex = regex

class KthreadPlugin(base.Plugin):
	r"""
	`kthread`::

	Allows tuning of kernel threads by setting their CPU affinities and
	scheduling parameters. The plugin re-implements functionality already
	present in the `scheduler` plugin. However, this plugin offers more
	flexibility, as it allows tuning of individual kernel threads.
	Multiple plugin instances can be defined,each addressing different groups
	of kernel threads.
	When using the `kthread` plugin, make sure to disable processing of kernel
	threads in the `scheduler` plugin by setting its option
	[option]`kthread_process=false`.
	===
	Tuning options are controlled by [option]`group` definitions.
	+
	A group definition has the form
	`group.<name> = <rule_prio>:<schedopts>:<affinity>:<regex>`
	+
	with four required fields:
	+
	--
	`rule_prio`::
	priority of the group within this plugin instance (lower number indicates
	higher priority)
	`schedopts`::
	desired scheduling policy and priority, or either "*" or an empty string
	to leave the scheduling options unchanged.
	The first character defines the policy

	- f: SCHED_FIFO
	- b: SCHED_BATCH
	- r: SCHED_RR
	- o: SCHED_OTHER
	- i: SCHED_IDLE

	The remainder is the desired priority in the range 0..99.
	For SCHED_OTHER, only a priority of 0 is allowed.
	Examples: `f50` to set SCHED_FIFO with priority 50, `o0` for SCHED_OTHER
	`affinity`::
	desired affinity (as cpulist string), or either "*" or an empty string
	to leave the affinity unchanged
	`regex`::
	regular expression to match kernel threads. Note that the thread name needs
	to match the full regex, i.e. matching happens with re.fullmatch().
	--
	The [option]`group` options of the `kthread` plugin differ from those of
	the `scheduler` plugin:

	- scheduling policy and priority are combined into one option
	- affinities are specified as cpulist strings instead of masks
	- regular expressions need to fully match the thread names
	- no square brackets are added to the kernel thread names

	Example:
	The `scheduler` definition

	group.ksoftirqd=0:f:2:*:^\[ksoftirqd

	is translated to the `kthread` definition

	group.ksoftirqd=0:f2:*:ksoftirqd.*
	"""
	def __init__(self, monitor_repository, storage_factory, hardware_inventory, device_matcher, device_matcher_udev, plugin_instance_factory, global_cfg, variables):
		super(KthreadPlugin, self).__init__(monitor_repository, storage_factory, hardware_inventory, device_matcher, device_matcher_udev, plugin_instance_factory, global_cfg, variables)
		self._has_dynamic_options = True
		self._kthreads = {}
		self._lock = threading.RLock()
		self._instance_count = 0

		try:
			self._scheduler_utils = SchedulerUtils()
		except AttributeError:
			self._scheduler_utils = SchedulerUtilsSchedutils()

		if have_perf:
			self._perf_setup()
		else:
			log.warning("python-perf unavailable. " \
				"Tuning will be applied to all currently running kthreads, but future kthreads will not be tuned. " \
				"You can try to (re)install the python(3)-perf package.")

	def cleanup(self):
		super(KthreadPlugin, self).cleanup()
		if have_perf:
			self._perf_shutdown()

	#
	# plugin-level methods: devices and plugin options
	#
	def _init_devices(self):
		super(KthreadPlugin, self)._init_devices()
		self._kthread_pids_unassigned = set()
		self._kthread_scan(initial=True)

	@classmethod
	def _get_config_options(cls):
		return {
			# nothing here, the group.* options are covered by self._has_dynamic_options
		}

	def _plugin_add_kthread(self, pid):
		"""Add kthread to the plugin for tuning (usually by one of the instances)"""
		for instance in self._instances.values():
			if self._get_matching_kthreads(instance, [pid]):
				self._instance_add_kthread(instance, pid)
				return
		self._kthread_pids_unassigned.add(pid)

	def _plugin_remove_kthread(self, pid):
		"""Remove kthread from the plugin (and from the instances)"""
		for instance in self._instances.values():
			self._instance_remove_kthread(instance, pid)

	#
	# instance-level methods: implement the Instance interface
	#
	def _instance_init(self, instance):
		instance._has_static_tuning = True
		instance._has_dynamic_tuning = False
		# kthreads handled by instance, assigned and processed
		instance._kthreads_assigned = set()
		instance._kthreads_processed = set()
		instance._tuning_active = False
		# process group.* options
		self._instance_prepare_matching(instance)
		# grab initial set of kthreads
		self._instance_acquire_kthreads(instance)

	def _instance_cleanup(self, instance):
		self._instance_release_kthreads(instance)

	def _instance_prepare_matching(self, instance):
		"""Process all group.* options and populate instance._groups"""
		groups = []
		for k, v in instance.options.items():
			# group definitions have the format:
			# group.<name> = <rule_prio>:<schedopts>:<affinity>:<regex>
			if not k.startswith("group."):
				continue
			name = k[len("group."):]
			opt = self._variables.expand(v).split(":", 3)
			if not len(opt) == 4:
				log.error("Invalid definition for '%s': need exactly 4 arguments" % k)
				continue
			opt_rule_prio, opt_schedopts, opt_affinity, opt_regex = opt
			# parse rule prio
			try:
				rule_prio = int(opt_rule_prio)
			except ValueError:
				log.error("Could not parse rule prio for '%s': '%s' is not a number" % (k, opt_rule_prio))
				continue
			# parse scheduling options
			policy, priority, affinity = None, None, None
			if opt_schedopts in ["", "*"]:
				pass
			elif len(opt_schedopts) > 1 and opt_schedopts[0] in self._scheduler_utils._dict_schedcfg2num.keys():
				policy = self._scheduler_utils.sched_cfg_to_num(opt_schedopts[0])
				try:
					priority = int(opt_schedopts[1:])
				except ValueError:
					log.error("Could not parse scheduling priority for '%s': '%s' is not a number" % (k, opt_schedopts[1:]))
					continue
				if policy == os.SCHED_OTHER and priority != 0:
					log.error("Could not parse scheduling priority for '%s': SCHED_OTHER requires priority 0" % k)
					continue
				if priority < 0 or priority > 99:
					log.error("Could not parse scheduling priority for '%s': value '%d' out of range" % (k, priority))
					continue
			else:
				log.error("Could not parse scheduling priority for '%s': '%s' has wrong format" % (k, opt_schedopts))
				continue
			if not opt_affinity in ["", "*"]:
				affinity = set(self._cmd.cpulist_unpack(opt_affinity))
				if len(affinity) == 0:
					log.error("Could not parse affinity for '%s': '%s' has wrong format" % (k, opt_affinity))
					continue
			sched = SchedOpts(policy=policy, priority=priority, affinity=affinity)
			# parse the regex
			try:
				regex = re.compile(opt_regex)
			except re.error as e:
				log.error("Could not compile regex for '%s': '%s'" % (k, e.msg))
				continue
			groups.append(GroupCmd(name, rule_prio, sched, regex))
		instance._groups = sorted(groups, key=lambda x: x.prio)

	def _get_instance_sched_options(self, instance, kthread):
		"""
		determine options an instance would set for a kthread, None if the
		instance would not set any (because none of the group.* regexes matches)
		"""
		for group in instance._groups:
			if group.regex.fullmatch(kthread.comm):
				return group.sched
		return None

	def _get_matching_kthreads(self, instance, pids):
		"""
		determine which threads fit the given instance
		"""
		matching_kthreads = set()
		for pid in pids:
			try:
				kthread = self._kthread_get(pid)
			except ThreadNoLongerExists:
				self._kthread_internal_remove(pid)
				continue
			if self._get_instance_sched_options(instance, kthread) is not None:
				matching_kthreads.add(pid)
		return matching_kthreads

	def _instance_add_kthread(self, instance, pid):
		"""add a kthread to an instance, and tune it"""
		with self._lock:
			if instance._tuning_active:
				try:
					kthread = self._kthread_get(pid)
					opts = self._get_instance_sched_options(instance, kthread)
					self._apply_kthread_tuning(kthread, opts)
					instance._kthreads_processed.add(pid)
				except ThreadNoLongerExists:
					self._kthread_internal_remove(pid)
			else:
				instance._kthreads_assigned.add(pid)

	def _instance_remove_kthread(self, instance, pid):
		"""remove a kthread from an instance, and unapply tuning"""
		with self._lock:
			if pid in instance._kthreads_assigned:
				instance._kthreads_assigned.remove(pid)
			elif pid in instance._kthreads_processed:
				try:
					instance._kthreads_processed.remove(pid)
					kthread = self._kthread_get(pid)
					self._restore_kthread_tuning(kthread)
				except ThreadNoLongerExists:
					self._kthread_internal_remove(pid)
			else:
				# kthread does not belong to instance. ignore.
				pass

	def _instance_transfer_kthread(self, instance_from, instance_to, pid):
		"""move a kthread from one instance to another, and seamlessly adapt tuning"""
		with self._lock:
			if pid in instance_from._kthreads_processed:
				instance_from._kthreads_processed.remove(pid)
			elif pid in instance_from._kthreads_assigned:
				instance_from._kthreads_assigned.remove(pid)
			if instance_to._tuning_active:
				try:
					kthread = self._kthread_get(pid)
					opts = self._get_instance_sched_options(instance_to, kthread)
					self._apply_kthread_tuning(kthread, opts)
					instance_to._kthreads_processed.add(pid)
				except ThreadNoLongerExists:
					self._kthread_internal_remove(pid)
			else:
				instance_to._kthreads_assigned.add(pid)

	def _instance_acquire_kthreads(self, instance):
		"""assign all matching kthreads to an instance"""
		# first the ones that are currently unassigned
		with self._lock:
			acquire_kthreads = self._get_matching_kthreads(instance, self._kthread_pids_unassigned)
			self._kthread_pids_unassigned -= acquire_kthreads
			for pid in acquire_kthreads:
				self._instance_add_kthread(instance, pid)
		# and then the ones from other instances
		for other_instance in self._instances.values():
			if (other_instance == instance or instance.priority > other_instance.priority or not hasattr(other_instance, "_kthreads_assigned")):
				continue
			transfer_kthreads = self._get_matching_kthreads(instance, other_instance._kthreads_assigned | other_instance._kthreads_processed)
			for pid in transfer_kthreads:
				self._instance_transfer_kthread(other_instance, instance, pid)

	def _instance_release_kthreads(self, instance):
		"""release all kthreads from an instance"""
		free_kthreads = instance._kthreads_assigned | instance._kthreads_processed
		# first the ones now claimed by other instances
		for other_instance in self._instances.values():
			if other_instance == instance:
				continue
			transfer_kthreads = self._get_matching_kthreads(other_instance, free_kthreads)
			for pid in list(transfer_kthreads):
				self._instance_transfer_kthread(instance, other_instance, pid)
				free_kthreads.remove(pid)
		# the remaining ones go back to unassigned
		with self._lock:
			for pid in free_kthreads:
				self._instance_remove_kthread(instance, pid)
				self._kthread_pids_unassigned.add(pid)

	def _instance_apply_static(self, instance):
		if self._instance_count == 0:
			# scan for kthreads that have appeared since plugin initialization
			self._kthread_scan(initial=False)
			if have_perf:
				self._perf_monitor_start()
		self._instance_count += 1
		with self._lock:
			instance._tuning_active = True
			for pid in list(instance._kthreads_assigned):
				instance._kthreads_assigned.remove(pid)
				try:
					kthread = self._kthread_get(pid)
					opts = self._get_instance_sched_options(instance, kthread)
					self._apply_kthread_tuning(kthread, opts)
					instance._kthreads_processed.add(pid)
				except ThreadNoLongerExists:
					self._kthread_internal_remove(pid)

	def _instance_verify_static(self, instance, ignore_missing, devices):
		result = True
		with self._lock:
			for pid in list(instance._kthreads_processed):
				try:
					kthread = self._kthread_get(pid)
					opts = self._get_instance_sched_options(instance, kthread)
					result &= self._verify_kthread_tuning(kthread, opts)
				except ThreadNoLongerExists:
					self._kthread_internal_remove(pid)
		return result

	def _instance_unapply_static(self, instance, rollback):
		with self._lock:
			instance._tuning_active = False
			for pid in list(instance._kthreads_processed):
				try:
					kthread = self._kthread_get(pid)
					if rollback == consts.ROLLBACK_FULL:
						self._restore_kthread_tuning(kthread)
						instance._kthreads_assigned.add(pid)
						instance._kthreads_processed.remove(pid)
				except ThreadNoLongerExists:
					self._kthread_internal_remove(pid)
		self._instance_count -= 1
		if self._instance_count == 0:
			if have_perf:
				self._perf_monitor_shutdown()

	#
	# internal bookkeeping (self._kthreads)
	# as these methods are called from the main thred and the perf monitor
	# thread, we need to lock all accesses to self._kthreads
	#
	def _kthread_scan(self, initial=False):
		"""Scan procfs for kernel threads and add them to our bookkeeping

		Args:
			initial (bool): is this the initial scan? passed on to _kthread_add()
		"""
		ps = procfs.pidstats()
		for pid in ps.keys():
			self._kthread_internal_add(pid, initial)

	def _kthread_internal_add(self, pid, initial=False):
		"""Add kernel thread to internal bookkeeping

		Args:
			pid (int): kernel thread pid
			initial (bool): is this the initial scan? if yes, then add the new
				kthread to _free_devices, else initiate hotplug mechanism via
				_add_device()
		"""
		try:
			proc = procfs.process(pid)
			if not self._is_kthread(proc):
				return
			kthread = KthreadInfo(proc)
		except (FileNotFoundError, ProcessLookupError):
			return

		with self._lock:
			if kthread.pid in self._kthreads:
				return
			self._kthreads[kthread.pid] = kthread
			if initial:
				self._kthread_pids_unassigned.add(kthread.pid)
			else:
				self._plugin_add_kthread(kthread.pid)
		log.debug("Added kthread %s" % kthread)

	def _kthread_internal_remove(self, pid):
		"""Remove kernel thread from internal bookkeeping

		Args:
			pid (int): kernel thread pid
		"""
		try:
			with self._lock:
				del self._kthreads[pid]
				self._plugin_remove_kthread(pid)
		except KeyError:
			return
		log.debug("Removed kthread %d" % pid)

	def _kthread_get(self, pid):
		"""Get KthreadInfo object for a given PID

		Args:
			pid (int): kernel thread pid
		"""
		try:
			with self._lock:
				return self._kthreads[pid]
		except KeyError:
			raise ThreadNoLongerExists()

	def _is_kthread(self, proc):
		"""helper to determine if a procfs process is a kernel thread"""
		return proc["stat"]["flags"] & procfs.pidstat.PF_KTHREAD != 0

	#
	# methods to interact with perf
	#
	def _perf_setup(self):
		self._cpus = perf.cpu_map()
		self._threads = perf.thread_map()
		self._evlist = perf.evlist(self._cpus, self._threads)
		evsel = perf.evsel(
			type=perf.TYPE_SOFTWARE,
			config=perf.COUNT_SW_DUMMY,
			task=1,
			comm=1,
			mmap=0,
			freq=0,
			wakeup_events=1,
			watermark=1,
			sample_type=perf.SAMPLE_TID|perf.SAMPLE_CPU,
		)
		evsel.open(cpus=self._cpus, threads=self._threads)
		self._evlist.add(evsel)
		self._evlist.mmap()

	def _perf_shutdown(self):
		if self._evlist:
			for fd in self._evlist.get_pollfd():
				os.close(fd.name)

	def _perf_monitor_start(self):
		self._terminate = threading.Event()
		self._thread = threading.Thread(target=self._perf_monitor_thread)
		self._thread.start()

	def _perf_monitor_shutdown(self):
		self._terminate.set()
		self._thread.join()

	def _perf_monitor_thread(self):
		"""
		Thread to handle notifications from perf

		New kthreads sometimes (e.g., `irq/*` threads) are spawned with default
		scheduling options and adapt their policy/priority themselves.
		This opens a race window, where we possibly change sched options
		before the thread itself does, leading to wrong settings, and also
		wrong "original" settings in case we roll back the tuning.
		So we delay tuning for newly created threads to reduce the chance of races.
		"""
		class NewThread(object):
			def __init__(self, ts, tid):
				self.ts, self.tid = ts, tid
		new_threads = []
		thread_add_delay_s = 1.0

		log.debug("perf monitor thread starting")
		poll = select.poll()
		fds = self._evlist.get_pollfd()
		for fd in fds:
			poll.register(fd)
		while not self._terminate.is_set():
			# process new threads when their delay has passed
			now = time.time()
			while len(new_threads) > 0 and now >= new_threads[0].ts:
				self._kthread_internal_add(new_threads.pop(0).tid)
			timeout_ms = 1000
			if len(new_threads) > 0:
				timeout_ms = min(timeout_ms, int((new_threads[0].ts - now) * 1000))
			if len(poll.poll(timeout_ms)) == 0:
				continue
			# we have new perf notifications
			now = time.time()
			have_events = True
			while have_events:
				have_events = False
				for cpu in self._cpus:
					event = self._evlist.read_on_cpu(cpu)
					if event and hasattr(event, "type"):
						have_events = True
						if event.type == perf.RECORD_COMM:
							new_threads.append(NewThread(now + thread_add_delay_s, event.tid))
						elif event.type == perf.RECORD_EXIT:
							self._kthread_internal_remove(event.tid)
		log.debug("perf monitor thread shutting down")

	#
	# methods for low-level manipulation of scheduling options
	# via SchedulerUtils from .plugin_scheduler
	#
	def _set_affinity(self, pid, affinity):
		try:
			self._scheduler_utils.set_affinity(pid, affinity)
		except OSError as e:
			if hasattr(e, "errno") and e.errno == errno.ESRCH:
				log.debug("Failed to set affinity of PID %d, the task vanished." % pid)
				raise ThreadNoLongerExists()
			else:
				try:
					proc = procfs.process(pid)
					changeable = not proc["stat"].is_bound_to_cpu()
				except (OSError, IOError):
					raise ThreadNoLongerExists()
				if not changeable:
					raise AffinityNotChangeable()
				log.error("Failed to set affinity of PID %d to '%s': %s" % (pid, affinity, e))
				raise e

	def _get_affinity(self, pid):
		try:
			return self._scheduler_utils.get_affinity(pid)
		except OSError as e:
			if hasattr(e, "errno") and e.errno == errno.ESRCH:
				log.debug("Failed to get affinity of PID %d, the task vanished." % pid)
				raise ThreadNoLongerExists()
			else:
				log.error("Failed to get affinity of PID %d: %s" % (pid, e))
				raise e

	def _set_schedopts(self, pid, policy, priority):
		try:
			self._scheduler_utils.set_scheduler(pid, policy, priority)
		except OSError as e:
			if hasattr(e, "errno") and e.errno == errno.ESRCH:
				log.debug("Failed to set scheduling of kthread %d, the task vanished." % pid)
				raise ThreadNoLongerExists()
			else:
				log.error("Failed to set scheduling of kthread %d: %s" % (pid, e))
				raise e

	def _get_schedopts(self, pid):
		try:
			return self._scheduler_utils.get_scheduler(pid), self._scheduler_utils.get_priority(pid)
		except OSError as e:
			if hasattr(e, "errno") and e.errno == errno.ESRCH:
				log.debug("Failed to get scheduling of kthread %d, the task vanished." % pid)
				raise ThreadNoLongerExists()
			else:
				log.error("Failed to get scheduling of kthread %d: %s" % (pid, e))
				raise e

	def _format_schedopts(self, policy, priority):
		return "%s:%d" % (self._scheduler_utils.sched_num_to_const(policy), priority)

	#
	# "high-level" methods that work on KthreadInfo objects:
	# apply tuning while saving original settings
	#
	def _apply_kthread_tuning(self, kthread, opts):
		if kthread.sched_orig is not None:
			return self._change_kthread_tuning(kthread, opts)

		current_affinity = self._get_affinity(kthread.pid)
		current_policy, current_priority = self._get_schedopts(kthread.pid)
		kthread.sched_orig = SchedOpts(policy=current_policy, priority=current_priority, affinity=current_affinity)

		if opts.affinity is not None and opts.affinity != current_affinity:
			try:
				self._set_affinity(kthread.pid, opts.affinity)
				kthread.affinity_changeable = True
				log.debug("Set CPU affinity of kthread %s to '%s'" % (kthread, opts.affinity))
				kthread.tuned_affinity = True
			except AffinityNotChangeable:
				kthread.affinity_changeable = False
				log.debug("The CPU affinity of kthread %s is not changeable" % kthread)
		if opts.policy is not None or opts.priority is not None:
			if opts.policy != current_policy or opts.priority != current_priority:
				self._set_schedopts(kthread.pid, opts.policy, opts.priority)
				log.debug("Set scheduling of kthread %s to '%s'"
						% (kthread, self._format_schedopts(opts.policy, opts.priority)))
				kthread.tuned_sched = True

	def _change_kthread_tuning(self, kthread, opts):
		if opts.affinity is None and kthread.tuned_affinity:
			self._set_affinity(kthread.pid, kthread.sched_orig.affinity)
			log.debug("Changed (restored) CPU affinity of kthread %s to '%s'" % (kthread, kthread.sched_orig.affinity))
			kthread.tuned_affinity = False
		elif opts.affinity is not None and kthread.affinity_changeable != False:
			try:
				self._set_affinity(kthread.pid, opts.affinity)
				kthread.affinity_changeable = True
				log.debug("Changed CPU affinity of kthread %s to '%s'" % (kthread, opts.affinity))
				kthread.tuned_affinity = True
			except AffinityNotChangeable:
				kthread.affinity_changeable = False
				log.debug("The CPU affinity of kthread %s is not changeable" % kthread)
		if opts.policy is None and opts.priority is None and kthread.tuned_sched:
			self._set_schedopts(kthread.pid, kthread.sched_orig.policy, kthread.sched_orig.priority)
			log.debug("Changed (restored) scheduling of kthread %s to '%s'"
					% (kthread, self._format_schedopts(kthread.sched_orig.policy, kthread.sched_orig.priority)))
			kthread.tuned_sched = False
		elif opts.policy is not None or opts.priority is not None:
			self._set_schedopts(kthread.pid, opts.policy, opts.priority)
			log.debug("Changed scheduling of kthread %s to '%s'"
					% (kthread, self._format_schedopts(opts.policy, opts.priority)))
			kthread.tuned_sched = True

	def _restore_kthread_tuning(self, kthread):
		opts = kthread.sched_orig
		current_affinity = self._get_affinity(kthread.pid)
		current_policy, current_priority = self._get_schedopts(kthread.pid)
		if kthread.affinity_changeable and opts.affinity != current_affinity:
			try:
				self._set_affinity(kthread.pid, opts.affinity)
				log.debug("Restored CPU affinity of kthread %s to '%s'"
						% (kthread, opts.affinity))
				kthread.tuned_affinity = False
			except AffinityNotChangeable:
				log.debug("Failed to restore CPU affinity of kthread %s to '%s'"
						% (kthread, opts.affinity))
		if opts.policy != current_policy or opts.priority != current_priority:
			self._set_schedopts(kthread.pid, opts.policy, opts.priority)
			log.debug("Restored scheduling of kthread %s to '%s'"
					% (kthread, self._format_schedopts(opts.policy, opts.priority)))
			kthread.tuned_sched = False
		kthread.sched_orig = None

	def _verify_kthread_tuning(self, kthread, opts):
		affinity_ok, priority_ok = True, True
		current_affinity = self._get_affinity(kthread.pid)
		current_policy, current_priority = self._get_schedopts(kthread.pid)
		if opts.affinity is not None and kthread.affinity_changeable:
			desc = "CPU affinity of kthread %s" % kthread
			current = self._cmd.cpulist2string(self._cmd.cpulist_pack(current_affinity))
			if opts.affinity == current_affinity:
				log.info(consts.STR_VERIFY_PROFILE_VALUE_OK % (desc, current))
			else:
				desired = self._cmd.cpulist2string(self._cmd.cpulist_pack(opts.affinity))
				log.error(consts.STR_VERIFY_PROFILE_VALUE_FAIL % (desc, current, desired))
				affinity_ok = False
		if opts.policy is not None or opts.priority is not None:
			desc = "scheduling of kthread %s" % kthread
			current = self._format_schedopts(current_policy, current_priority)
			if opts.policy == current_policy and opts.priority == current_priority:
				log.info(consts.STR_VERIFY_PROFILE_VALUE_OK % (desc, current))
			else:
				desired = self._format_schedopts(opts.policy, opts.priority)
				log.error(consts.STR_VERIFY_PROFILE_VALUE_FAIL % (desc, current, desired))
				priority_ok = False
		return affinity_ok and priority_ok
