# code for cores isolation was inspired by Tuna implementation
# perf code was borrowed from kernel/tools/perf/python/twatch.py
# thanks to Arnaldo Carvalho de Melo <acme@redhat.com>

from . import base
from .decorators import *
import tuned.logs
import re
from subprocess import *
import threading
import perf
import select
import tuned.consts as consts
import procfs
from tuned.utils.commands import commands
import errno
import os
import collections
import math
# Check existence of scheduler API in os module
try:
	os.SCHED_FIFO
except AttributeError:
	import schedutils

log = tuned.logs.get()

class SchedulerParams(object):
	def __init__(self, cmd, cmdline = None, scheduler = None,
			priority = None, affinity = None, cgroup = None):
		self._cmd = cmd
		self.cmdline = cmdline
		self.scheduler = scheduler
		self.priority = priority
		self.affinity = affinity
		self.cgroup = cgroup

	@property
	def affinity(self):
		if self._affinity is None:
			return None
		else:
			return self._cmd.bitmask2cpulist(self._affinity)

	@affinity.setter
	def affinity(self, value):
		if value is None:
			self._affinity = None
		else:
			self._affinity = self._cmd.cpulist2bitmask(value)

class IRQAffinities(object):
	def __init__(self):
		self.irqs = {}
		self.default = None
		# IRQs that don't support changing CPU affinity:
		self.unchangeable = []

class SchedulerUtils(object):
	"""
	Class encapsulating scheduler implementation in os module
	"""

	_dict_schedcfg2schedconst = {
		"f": "SCHED_FIFO",
		"b": "SCHED_BATCH",
		"r": "SCHED_RR",
		"o": "SCHED_OTHER",
		"i": "SCHED_IDLE",
	}

	def __init__(self):
		# {"f": os.SCHED_FIFO...}
		self._dict_schedcfg2num = dict((k, getattr(os, name)) for k, name in self._dict_schedcfg2schedconst.items())
		# { os.SCHED_FIFO: "SCHED_FIFO"... }
		self._dict_num2schedconst = dict((getattr(os, name), name) for name in self._dict_schedcfg2schedconst.values())

	def sched_cfg_to_num(self, str_scheduler):
		return self._dict_schedcfg2num.get(str_scheduler)

	# Reimplementation of schedstr from schedutils for logging purposes
	def sched_num_to_const(self, scheduler):
		return self._dict_num2schedconst.get(scheduler)

	def get_scheduler(self, pid):
		return os.sched_getscheduler(pid)

	def set_scheduler(self, pid, sched, prio):
		os.sched_setscheduler(pid, sched, os.sched_param(prio))

	def get_affinity(self, pid):
		return os.sched_getaffinity(pid)

	def set_affinity(self, pid, affinity):
		os.sched_setaffinity(pid, affinity)

	def get_priority(self, pid):
		return os.sched_getparam(pid).sched_priority

	def get_priority_min(self, sched):
		return os.sched_get_priority_min(sched)

	def get_priority_max(self, sched):
		return os.sched_get_priority_max(sched)

class SchedulerUtilsSchedutils(SchedulerUtils):
	"""
	Class encapsulating scheduler implementation in schedutils module
	"""
	def __init__(self):
		# { "f": schedutils.SCHED_FIFO... }
		self._dict_schedcfg2num = dict((k, getattr(schedutils, name)) for k, name in self._dict_schedcfg2schedconst.items())
		# { schedutils.SCHED_FIFO: "SCHED_FIFO"... }
		self._dict_num2schedconst = dict((getattr(schedutils, name), name) for name in self._dict_schedcfg2schedconst.values())

	def get_scheduler(self, pid):
		return schedutils.get_scheduler(pid)

	def set_scheduler(self, pid, sched, prio):
		schedutils.set_scheduler(pid, sched, prio)

	def get_affinity(self, pid):
		return schedutils.get_affinity(pid)

	def set_affinity(self, pid, affinity):
		schedutils.set_affinity(pid, affinity)

	def get_priority(self, pid):
		return schedutils.get_priority(pid)

	def get_priority_min(self, sched):
		return schedutils.get_priority_min(sched)

	def get_priority_max(self, sched):
		return schedutils.get_priority_max(sched)

class SchedulerPlugin(base.Plugin):
	r"""
	Allows tuning of scheduling priorities, process/thread/IRQ
	affinities, and CPU isolation.

	To prevent processes/threads/IRQs from using certain CPUs, use
	the [option]`isolated_cores` option. It changes process/thread
	affinities, IRQs affinities and it sets `default_smp_affinity`
	for IRQs. The CPU affinity mask is adjusted for all processes and
	threads matching [option]`ps_whitelist` option subject to success
	of the `sched_setaffinity()` system call. The default setting of
	the [option]`ps_whitelist` regular expression is `.*` to match all
	processes and thread names. To exclude certain processes and threads
	use [option]`ps_blacklist` option. The value of this option is also
	interpreted as a regular expression and process/thread names (`ps -eo
	cmd`) are matched against that expression. Profile rollback allows
	all matching processes and threads to run on all CPUs and restores
	the IRQ settings prior to the profile application.

	Multiple regular expressions for [option]`ps_whitelist`
	and [option]`ps_blacklist` options are allowed and separated by
	`;`. Quoted semicolon `\;` is taken literally.

	.Isolate CPUs 2-4
	====
	----
	[scheduler]
	isolated_cores=2-4
	ps_blacklist=.*pmd.*;.*PMD.*;^DPDK;.*qemu-kvm.*
	----
	Isolate CPUs 2-4 while ignoring processes and threads matching
	`ps_blacklist` regular expressions.
	====

	The [option]`irq_process` option controls whether the scheduler plugin
	applies the `isolated_cores` parameter to IRQ affinities. The default
	value is `true`, which means that the scheduler plugin will move all
	possible IRQs away from the isolated cores. When `irq_process` is set
	to `false`, the plugin will not change any IRQ affinities.

	The [option]`default_irq_smp_affinity` option controls the values
	*TuneD* writes to `/proc/irq/default_smp_affinity`. The file specifies
	default affinity mask that applies to all non-active IRQs. Once an
	IRQ is allocated/activated its affinity bitmask will be set to the
	default mask.

	The following values are supported:

	* `calc`
	+
	The content of `/proc/irq/default_smp_affinity` will be calculated
	from the `isolated_cores` parameter. Non-isolated cores
	are calculated as an inversion of the `isolated_cores`. Then
	the intersection of the non-isolated cores and the previous
	content of `/proc/irq/default_smp_affinity` is written to
	`/proc/irq/default_smp_affinity`. If the intersection is
	an empty set, then just the non-isolated cores are written to
	`/proc/irq/default_smp_affinity`. This behavior is the default if
	the parameter `default_irq_smp_affinity` is omitted.

	* `ignore`
	+
	*TuneD* will not touch `/proc/irq/default_smp_affinity`.

	* an explicit cpulist
	+
	The cpulist (such as `1,3-4`) is unpacked and written directly to
	`/proc/irq/default_smp_affinity`.

	.An explicit CPU list to set the default IRQ smp affinity to CPUs 0 and 2
	====
	----
	[scheduler]
	isolated_cores=1,3
	default_irq_smp_affinity=0,2
	----
	====

	To adjust scheduling policy, priority and affinity for a group of
	processes/threads, use the following syntax.

	[subs="+quotes,+macros"]
	----
	group.__groupname__=__rule_prio__:__sched__:__prio__:__affinity__:__regex__
	----

	Here, `__rule_prio__` defines internal *TuneD* priority of the
	rule. Rules are sorted based on priority. This is needed for
	inheritence to be able to reorder previously defined rules. Equal
	`__rule_prio__` rules should be processed in the order they were
	defined. However, this is Python interpreter dependant. To disable
	an inherited rule for `__groupname__` use:

	[subs="+quotes,+macros"]
	----
	group.__groupname__=
	----

	`__sched__` must be one of:
	*`f`* for FIFO,
	*`b`* for batch,
	*`r`* for round robin,
	*`o`* for other,
	*`*`* do not change.

	`__affinity__` is CPU affinity in hexadecimal. Use `*` for no change.

	`__prio__` scheduling priority (see `chrt -m`).

	`__regex__` is Python regular expression. It is matched against the output of:

	[subs="+quotes,+macros"]
	----
	ps -eo cmd
	----

	Any given process name may match more than one group. In such a case,
	the priority and scheduling policy are taken from the last matching
	`__regex__`.

	.Setting scheduling policy and priorities to kernel threads and watchdog
	====
	----
	[scheduler]
	group.kthreads=0:*:1:*:\[.*\]$
	group.watchdog=0:f:99:*:\[watchdog.*\]
	----
	====

	The scheduler plug-in uses perf event loop to catch newly created
	processes. By default it listens to `perf.RECORD_COMM` and
	`perf.RECORD_EXIT` events. By setting [option]`perf_process_fork`
	option to `true`, `perf.RECORD_FORK` events will be also listened
	to. In other words, child processes created by the `fork()` system
	call will be processed. Since child processes inherit CPU affinity
	from their parents, the scheduler plug-in usually does not need to
	explicitly process these events. As processing perf events can
	pose a significant CPU overhead, the [option]`perf_process_fork`
	option parameter is set to `false` by default. Due to this, child
	processes are not processed by the scheduler plug-in.

	The CPU overhead of the scheduler plugin can be mitigated by using
	the scheduler [option]`runtime` option and setting it to `0`. This
	will completely disable the dynamic scheduler functionality and the
	perf events will not be monitored and acted upon. The disadvantage
	ot this approach is the procees/thread tuning will be done only at
	profile application.

	.Disabling the scheduler dynamic functionality
	====
	----
	[scheduler]
	runtime=0
	isolated_cores=1,3
	----
	====

	NOTE: For perf events, memory mapped buffer is used. Under heavy load
	the buffer may overflow. In such cases the `scheduler` plug-in
	may start missing events and failing to process some newly created
	processes. Increasing the buffer size may help. The buffer size can
	be set with the [option]`perf_mmap_pages` option. The value of this
	parameter has to expressed in powers of 2. If it is not the power
	of 2, the nearest higher power of 2 value is calculated from it
	and this calculated value used. If the [option]`perf_mmap_pages`
	option is omitted, the default kernel value is used.

	The scheduler plug-in supports process/thread confinement using
	cgroups v1.

	[option]`cgroup_mount_point` option specifies the path to mount the
	cgroup filesystem or where *TuneD* expects it to be mounted. If unset,
	`/sys/fs/cgroup/cpuset` is expected.

	If [option]`cgroup_groups_init` option is set to `1` *TuneD*
	will create (and remove) all cgroups defined with the `cgroup*`
	options. This is the default behavior. If it is set to `0` the
	cgroups need to be preset by other means.

	If [option]`cgroup_mount_point_init` option is set to `1`,
	*TuneD* will create (and remove) the cgroup mountpoint. It implies
	`cgroup_groups_init = 1`. If set to `0` the cgroups mount point
	needs to be preset by other means. This is the default behavior.

	The [option]`cgroup_for_isolated_cores` option is the cgroup
	name used for the [option]`isolated_cores` option functionality. For
	example, if a system has 4 CPUs, `isolated_cores=1` means that all
	processes/threads will be moved to CPUs 0,2-3.
	The scheduler plug-in will isolate the specified core by writing
	the calculated CPU affinity to the `cpuset.cpus` control file of
	the specified cgroup and move all the matching processes/threads to
	this group. If this option is unset, classic cpuset affinity using
	`sched_setaffinity()` will be used.

	[option]`cgroup.__cgroup_name__` option defines affinities for
	arbitrary cgroups. Even hierarchic cgroups can be used, but the
	hieararchy needs to be specified in the correct order. Also *TuneD*
	does not do any sanity checks here, with the exception that it forces
	the cgroup to be under [option]`cgroup_mount_point`.

	The syntax of the scheduler option starting with `group.` has been
	augmented to use `cgroup.__cgroup_name__` instead of the hexadecimal
	`__affinity__`. The matching processes will be moved to the cgroup
	`__cgroup_name__`. It is also possible to use cgroups which have
	not been defined by the [option]`cgroup.` option as described above,
	i.e. cgroups not managed by *TuneD*.

	All cgroup names are sanitized by replacing all all dots (`.`) with
	slashes (`/`). This is to prevent the plug-in from writing outside
	[option]`cgroup_mount_point`.

	.Using cgroups v1 with the scheduler plug-in
	====
	----
	[scheduler]
	cgroup_mount_point=/sys/fs/cgroup/cpuset
	cgroup_mount_point_init=1
	cgroup_groups_init=1
	cgroup_for_isolated_cores=group
	cgroup.group1=2
	cgroup.group2=0,2
	
	group.ksoftirqd=0:f:2:cgroup.group1:ksoftirqd.*
	ps_blacklist=ksoftirqd.*;rcuc.*;rcub.*;ktimersoftd.*
	isolated_cores=1
	----
	Cgroup `group1` has the affinity set to CPU 2 and the cgroup `group2`
	to CPUs 0,2. Given a 4 CPU setup, the [option]`isolated_cores=1`
	option causes all processes/threads to be moved to CPU
	cores 0,2-3. Processes/threads that are blacklisted by the
	[option]`ps_blacklist` regular expression will not be moved.
	
	The scheduler plug-in will isolate the specified core by writing the
	CPU affinity 0,2-3 to the `cpuset.cpus` control file of the `group`
	and move all the matching processes/threads to this cgroup.
	====

	Option [option]`cgroup_ps_blacklist` allows excluding processes
	which belong to the blacklisted cgroups. The regular expression specified
	by this option is matched against cgroup hierarchies from
	`/proc/PID/cgroups`. Cgroups v1 hierarchies from `/proc/PID/cgroups`
	are separated by commas ',' prior to regular expression matching. The
	following is an example of content against which the regular expression
	is matched against: `10:hugetlb:/,9:perf_event:/,8:blkio:/`

	Multiple regular expressions can be separated by semicolon ';'. The
	semicolon represents a logical 'or' operator.

	.Cgroup-based exclusion of processes from the scheduler
	====
	----
	[scheduler]
	isolated_cores=1
	cgroup_ps_blacklist=:/daemons\b
	----
	The scheduler plug-in will move all processes away from core 1 except processes which
	belong to cgroup '/daemons'. The '\b' is a regular expression
	metacharacter that matches a word boundary.
	----
	[scheduler]
	isolated_cores=1
	cgroup_ps_blacklist=\b8:blkio:
	----
	The scheduler plug-in will exclude all processes which belong to a cgroup
	with hierarchy-ID 8 and controller-list blkio.
	====

	Recent kernels moved some `sched_` and `numa_balancing_` kernel run-time
	parameters from `/proc/sys/kernel`, managed by the `sysctl` utility, to
	`debugfs`, typically mounted under `/sys/kernel/debug`.  TuneD provides an
	abstraction mechanism for the following parameters via the scheduler plug-in:
	[option]`sched_min_granularity_ns`, [option]`sched_latency_ns`,
	[option]`sched_wakeup_granularity_ns`, [option]`sched_tunable_scaling`,
	[option]`sched_migration_cost_ns`, [option]`sched_nr_migrate`,
	[option]`numa_balancing_scan_delay_ms`,
	[option]`numa_balancing_scan_period_min_ms`,
	[option]`numa_balancing_scan_period_max_ms` and
	[option]`numa_balancing_scan_size_mb`.
	Based on the kernel used, TuneD will write the specified value to the correct
	location.

	.Set tasks' "cache hot" value for migration decisions.
	====
	----
	[scheduler]
	sched_migration_cost_ns=500000
	----
	On the old kernels, this is equivalent to:
	----
	[sysctl]
	kernel.sched_migration_cost_ns=500000
	----
	that is, value `500000` will be written to `/proc/sys/kernel/sched_migration_cost_ns`.
	However, on more recent kernels, the value `500000` will be written to
	`/sys/kernel/debug/sched/migration_cost_ns`.
	====
	"""

	def __init__(self, monitor_repository, storage_factory, hardware_inventory, device_matcher, device_matcher_udev, plugin_instance_factory, global_cfg, variables):
		super(SchedulerPlugin, self).__init__(monitor_repository, storage_factory, hardware_inventory, device_matcher, device_matcher_udev, plugin_instance_factory, global_cfg, variables)
		self._has_dynamic_options = True
		self._daemon = consts.CFG_DEF_DAEMON
		self._sleep_interval = int(consts.CFG_DEF_SLEEP_INTERVAL)
		if global_cfg is not None:
			self._daemon = global_cfg.get_bool(consts.CFG_DAEMON, consts.CFG_DEF_DAEMON)
			self._sleep_interval = int(global_cfg.get(consts.CFG_SLEEP_INTERVAL, consts.CFG_DEF_SLEEP_INTERVAL))
		self._cmd = commands()
		# helper variable utilized for showing hint only once that the error may be caused by Secure Boot
		self._secure_boot_hint = None
		# paths cache for sched_ and numa_ tunings
		self._sched_knob_paths_cache = {}
		# default is to whitelist all and blacklist none
		self._ps_whitelist = ".*"
		self._ps_blacklist = ""
		self._cgroup_ps_blacklist_re = ""
		self._cpus = perf.cpu_map()
		self._scheduler_storage_key = self._storage_key(
				command_name = "scheduler")
		self._irq_process = True
		self._irq_storage_key = self._storage_key(
				command_name = "irq")
		self._evlist = None
		try:
			self._scheduler_utils = SchedulerUtils()
		except AttributeError:
			self._scheduler_utils = SchedulerUtilsSchedutils()

	def _calc_mmap_pages(self, mmap_pages):
		if mmap_pages is None:
			return None
		try:
			mp = int(mmap_pages)
		except ValueError:
			return 0
		if mp <= 0:
			return 0
		# round up to the nearest power of two value
		return int(2 ** math.ceil(math.log(mp, 2)))

	def _instance_init(self, instance):
		instance._evlist = None
		instance._has_dynamic_tuning = False
		instance._has_static_tuning = True
		# this is hack, runtime_tuning should be covered by dynamic_tuning configuration
		# TODO: add per plugin dynamic tuning configuration and use dynamic_tuning configuration
		# instead of runtime_tuning
		instance._runtime_tuning = True

		# FIXME: do we want to do this here?
		# recover original values in case of crash
		self._scheduler_original = self._storage.get(
				self._scheduler_storage_key, {})
		if len(self._scheduler_original) > 0:
			log.info("recovering scheduling settings from previous run")
			self._restore_ps_affinity()
			self._scheduler_original = {}
			self._storage.unset(self._scheduler_storage_key)

		self._cgroups_original_affinity = dict()

		# calculated by isolated_cores setter
		self._affinity = None

		self._cgroup_affinity_initialized = False
		self._cgroup = None
		self._cgroups = collections.OrderedDict([(self._sanitize_cgroup_path(option[7:]), self._variables.expand(affinity))
			for option, affinity in instance.options.items() if option[:7] == "cgroup." and len(option) > 7])

		instance._scheduler = instance.options

		perf_mmap_pages_raw = self._variables.expand(instance.options["perf_mmap_pages"])
		perf_mmap_pages = self._calc_mmap_pages(perf_mmap_pages_raw)
		if perf_mmap_pages == 0:
			log.error("Invalid 'perf_mmap_pages' value specified: '%s', using default kernel value" % perf_mmap_pages_raw)
			perf_mmap_pages = None
		if perf_mmap_pages is not None and str(perf_mmap_pages) != perf_mmap_pages_raw:
			log.info("'perf_mmap_pages' value has to be power of two, specified: '%s', using: '%d'" %
				(perf_mmap_pages_raw, perf_mmap_pages))
		for k in instance._scheduler:
			instance._scheduler[k] = self._variables.expand(instance._scheduler[k])
		if self._cmd.get_bool(instance._scheduler.get("runtime", 1)) == "0":
			instance._runtime_tuning = False
		instance._terminate = threading.Event()
		if self._daemon and instance._runtime_tuning:
			try:
				instance._threads = perf.thread_map()
				evsel = perf.evsel(type = perf.TYPE_SOFTWARE,
					config = perf.COUNT_SW_DUMMY,
					task = 1, comm = 1, mmap = 0, freq = 0,
					wakeup_events = 1, watermark = 1,
					sample_type = perf.SAMPLE_TID | perf.SAMPLE_CPU)
				evsel.open(cpus = self._cpus, threads = instance._threads)
				instance._evlist = perf.evlist(self._cpus, instance._threads)
				instance._evlist.add(evsel)
				if perf_mmap_pages is None:
					instance._evlist.mmap()
				else:
					instance._evlist.mmap(pages = perf_mmap_pages)
			# no perf
			except:
				instance._runtime_tuning = False

	def _instance_cleanup(self, instance):
		if instance._evlist:
			for fd in instance._evlist.get_pollfd():
				os.close(fd.name)

	@classmethod
	def _get_config_options(cls):
		return {
			"isolated_cores": None,
			"cgroup_mount_point": consts.DEF_CGROUP_MOUNT_POINT,
			"cgroup_mount_point_init": False,
			"cgroup_groups_init": True,
			"cgroup_for_isolated_cores": None,
			"cgroup_ps_blacklist": None,
			"ps_whitelist": None,
			"ps_blacklist": None,
			"irq_process": True,
			"default_irq_smp_affinity": "calc",
			"perf_mmap_pages": None,
			"perf_process_fork": "false",
			"sched_min_granularity_ns": None,
			"sched_latency_ns": None,
			"sched_wakeup_granularity_ns": None,
			"sched_tunable_scaling": None,
			"sched_migration_cost_ns": None,
			"sched_nr_migrate": None,
			"numa_balancing_scan_delay_ms": None,
			"numa_balancing_scan_period_min_ms": None,
			"numa_balancing_scan_period_max_ms": None,
			"numa_balancing_scan_size_mb": None
		}

	def _sanitize_cgroup_path(self, value):
		return str(value).replace(".", "/") if value is not None else None

	# Raises OSError, IOError
	def _get_cmdline(self, process):
		if not isinstance(process, procfs.process):
			pid = process
			process = procfs.process(pid)
		cmdline = procfs.process_cmdline(process)
		if self._is_kthread(process):
			cmdline = "[" + cmdline + "]"
		return cmdline

	# Raises OSError, IOError
	def get_processes(self):
		ps = procfs.pidstats()
		ps.reload_threads()
		processes = {}
		for proc in ps.values():
			try:
				cmd = self._get_cmdline(proc)
				pid = proc["pid"]
				processes[pid] = cmd
				if "threads" in proc:
					for pid in proc["threads"].keys():
						cmd = self._get_cmdline(proc)
						processes[pid] = cmd
			except (OSError, IOError) as e:
				if e.errno == errno.ENOENT \
						or e.errno == errno.ESRCH:
					continue
				else:
					raise
		return processes

	# Raises OSError
	# Raises SystemError with old (pre-0.4) python-schedutils
	# instead of OSError
	# If PID doesn't exist, errno == ESRCH
	def _get_rt(self, pid):
		scheduler = self._scheduler_utils.get_scheduler(pid)
		sched_str = self._scheduler_utils.sched_num_to_const(scheduler)
		priority = self._scheduler_utils.get_priority(pid)
		log.debug("Read scheduler policy '%s' and priority '%d' of PID '%d'"
				% (sched_str, priority, pid))
		return (scheduler, priority)

	def _set_rt(self, pid, sched, prio):
		sched_str = self._scheduler_utils.sched_num_to_const(sched)
		log.debug("Setting scheduler policy to '%s' and priority to '%d' of PID '%d'."
				% (sched_str, prio, pid))
		try:
			prio_min = self._scheduler_utils.get_priority_min(sched)
			prio_max = self._scheduler_utils.get_priority_max(sched)
			if prio < prio_min or prio > prio_max:
				log.error("Priority for %s must be in range %d - %d. '%d' was given."
						% (sched_str, prio_min,
						prio_max, prio))
		# Workaround for old (pre-0.4) python-schedutils which raised
		# SystemError instead of OSError
		except (SystemError, OSError) as e:
			log.error("Failed to get allowed priority range: %s"
					% e)
		try:
			self._scheduler_utils.set_scheduler(pid, sched, prio)
		except (SystemError, OSError) as e:
			if hasattr(e, "errno") and e.errno == errno.ESRCH:
				log.debug("Failed to set scheduling parameters of PID %d, the task vanished."
						% pid)
			else:
				log.error("Failed to set scheduling parameters of PID %d: %s"
						% (pid, e))

	# process is a procfs.process object
	# Raises OSError, IOError
	def _is_kthread(self, process):
		return process["stat"]["flags"] & procfs.pidstat.PF_KTHREAD != 0

	# Returns True if we can ignore a failed affinity change of
	# a process with the given PID and therefore not report it as an error.
	def _ignore_set_affinity_error(self, pid):
		try:
			process = procfs.process(pid)
			if process["stat"]["state"] == "Z":
				log.debug("Affinity of zombie task with PID %d could not be changed."
						% pid)
				return True
			if process["stat"].is_bound_to_cpu():
				if self._is_kthread(process):
					log.debug("Affinity of kernel thread with PID %d cannot be changed, the task's affinity mask is fixed."
							% pid)
				else:
					log.warning("Affinity of task with PID %d cannot be changed, the task's affinity mask is fixed."
							% pid)
				return True
		except (OSError, IOError) as e:
			if e.errno == errno.ENOENT or e.errno == errno.ESRCH:
				log.debug("Failed to get task info for PID %d, the task vanished."
						% pid)
				return True
			log.error("Failed to get task info for PID %d: %s"
					% (pid, e))
		except (AttributeError, KeyError) as e:
			log.error("Failed to get task info for PID %d: %s"
					% (pid, e))
		return False

	def _store_orig_process_rt(self, pid, scheduler, priority):
		try:
			params = self._scheduler_original[pid]
		except KeyError:
			params = SchedulerParams(self._cmd)
			self._scheduler_original[pid] = params
		if params.scheduler is None and params.priority is None:
			params.scheduler = scheduler
			params.priority = priority

	def _tune_process_rt(self, pid, sched, prio):
		cont = True
		if sched is None and prio is None:
			return cont
		try:
			(prev_sched, prev_prio) = self._get_rt(pid)
			if sched is None:
				sched = prev_sched
			self._set_rt(pid, sched, prio)
			self._store_orig_process_rt(pid, prev_sched, prev_prio)
		except (SystemError, OSError) as e:
			if hasattr(e, "errno") and e.errno == errno.ESRCH:
				log.debug("Failed to read scheduler policy of PID %d, the task vanished."
						% pid)
				if pid in self._scheduler_original:
					del self._scheduler_original[pid]
				cont = False
			else:
				log.error("Refusing to set scheduler and priority of PID %d, reading original scheduling parameters failed: %s"
						% (pid, e))
		return cont

	def _is_cgroup_affinity(self, affinity):
		return str(affinity)[:7] == "cgroup."

	def _store_orig_process_affinity(self, pid, affinity, is_cgroup = False):
		try:
			params = self._scheduler_original[pid]
		except KeyError:
			params = SchedulerParams(self._cmd)
			self._scheduler_original[pid] = params
		if params.affinity is None and params.cgroup is None:
			if is_cgroup:
				params.cgroup = affinity
			else:
				params.affinity = affinity

	def _get_cgroup_affinity(self, pid):
		# we cannot use procfs, because it uses comma ',' delimiter which
		# can be ambiguous
		for l in self._cmd.read_file("%s/%s/%s" % (consts.PROCFS_MOUNT_POINT, str(pid), "cgroup"), no_error = True).split("\n"):
			try:
				cgroup = l.split(":cpuset:")[1][1:]
				return cgroup if cgroup != "" else "/"
			except IndexError:
				pass
		return "/"

	# it can be arbitrary cgroup even cgroup we didn't set, but it needs to be
	# under "cgroup_mount_point"
	def _set_cgroup(self, pid, cgroup):
		cgroup = self._sanitize_cgroup_path(cgroup)
		path = self._cgroup_mount_point
		if cgroup != "/":
			path = "%s/%s" % (path, cgroup)
		self._cmd.write_to_file("%s/tasks" % path, str(pid), no_error = True)

	def _parse_cgroup_affinity(self, cgroup):
		# "cgroup.CGROUP"
		cgroup = cgroup[7:]
		# this should be faster than string comparison
		is_cgroup = not isinstance(cgroup, list) and len(cgroup) > 0
		return is_cgroup, cgroup

	def _tune_process_affinity(self, pid, affinity, intersect = False):
		cont = True
		if affinity is None:
			return cont
		try:
			(is_cgroup, cgroup) = self._parse_cgroup_affinity(affinity)
			if is_cgroup:
				prev_affinity = self._get_cgroup_affinity(pid)
				self._set_cgroup(pid, cgroup)
			else:
				prev_affinity = self._get_affinity(pid)
				if intersect:
					affinity = self._get_intersect_affinity(
							prev_affinity, affinity,
							affinity)
				self._set_affinity(pid, affinity)
			self._store_orig_process_affinity(pid,
					prev_affinity, is_cgroup)
		except (SystemError, OSError) as e:
			if hasattr(e, "errno") and e.errno == errno.ESRCH:
				log.debug("Failed to read affinity of PID %d, the task vanished."
						% pid)
				if pid in self._scheduler_original:
					del self._scheduler_original[pid]
				cont = False
			else:
				log.error("Refusing to set CPU affinity of PID %d, reading original affinity failed: %s"
						% (pid, e))
		return cont

	#tune process and store previous values
	def _tune_process(self, pid, cmd, sched, prio, affinity):
		cont = self._tune_process_rt(pid, sched, prio)
		if not cont:
			return
		cont = self._tune_process_affinity(pid, affinity)
		if not cont or pid not in self._scheduler_original:
			return
		self._scheduler_original[pid].cmdline = cmd

	def _convert_sched_params(self, str_scheduler, str_priority):
		scheduler = self._scheduler_utils.sched_cfg_to_num(str_scheduler)
		if scheduler is None and str_scheduler != "*":
			log.error("Invalid scheduler: %s. Scheduler and priority will be ignored."
					% str_scheduler)
			return (None, None)
		else:
			try:
				priority = int(str_priority)
			except ValueError:
				log.error("Invalid priority: %s. Scheduler and priority will be ignored."
							% str_priority)
				return (None, None)
		return (scheduler, priority)

	def _convert_affinity(self, str_affinity):
		if str_affinity == "*":
			affinity = None
		elif self._is_cgroup_affinity(str_affinity):
			affinity = str_affinity
		else:
			affinity = self._cmd.hex2cpulist(str_affinity)
			if not affinity:
				log.error("Invalid affinity: %s. It will be ignored."
						% str_affinity)
				affinity = None
		return affinity

	def _convert_sched_cfg(self, vals):
		(rule_prio, scheduler, priority, affinity, regex) = vals
		(scheduler, priority) = self._convert_sched_params(
				scheduler, priority)
		affinity = self._convert_affinity(affinity)
		return (rule_prio, scheduler, priority, affinity, regex)

	def _cgroup_create_group(self, cgroup):
		path = "%s/%s" % (self._cgroup_mount_point, cgroup)
		try:
			os.mkdir(path, consts.DEF_CGROUP_MODE)
		except OSError as e:
			log.error("Unable to create cgroup '%s': %s" % (path, e))
		if (not self._cmd.write_to_file("%s/%s" % (path, "cpuset.mems"),
				self._cmd.read_file("%s/%s" % (self._cgroup_mount_point, "cpuset.mems"), no_error = True),
				no_error = True)):
					log.error("Unable to initialize 'cpuset.mems ' for cgroup '%s'" % path)

	def _cgroup_initialize_groups(self):
		if self._cgroup is not None and not self._cgroup in self._cgroups:
			self._cgroup_create_group(self._cgroup)
		for cg in self._cgroups:
			self._cgroup_create_group(cg)

	def _cgroup_initialize(self):
		log.debug("Initializing cgroups settings")
		try:
			os.makedirs(self._cgroup_mount_point, consts.DEF_CGROUP_MODE)
		except OSError as e:
			log.error("Unable to create cgroup mount point: %s" % e)
		(ret, out) = self._cmd.execute(["mount", "-t", "cgroup", "-o", "cpuset", "cpuset", self._cgroup_mount_point])
		if ret != 0:
			log.error("Unable to mount '%s'" % self._cgroup_mount_point)

	def _remove_dir(self, cgroup):
		try:
			os.rmdir(cgroup)
		except OSError as e:
			log.error("Unable to remove directory '%s': %s" % (cgroup, e))

	def _cgroup_finalize_groups(self):
		for cg in reversed(self._cgroups):
			self._remove_dir("%s/%s" % (self._cgroup_mount_point, cg))
		if self._cgroup is not None and not self._cgroup in self._cgroups:
			self._remove_dir("%s/%s" % (self._cgroup_mount_point, self._cgroup))

	def _cgroup_finalize(self):
		log.debug("Removing cgroups settings")
		(ret, out) = self._cmd.execute(["umount", self._cgroup_mount_point])
		if ret != 0:
			log.error("Unable to umount '%s'" % self._cgroup_mount_point)
			return False
		self._remove_dir(self._cgroup_mount_point)
		d = os.path.dirname(self._cgroup_mount_point)
		if (d != "/"):
			self._remove_dir(d)

	def _cgroup_set_affinity_one(self, cgroup, affinity, backup = False):
		if affinity != "":
			log.debug("Setting cgroup '%s' affinity to '%s'" % (cgroup, affinity))
		else:
			log.debug("Skipping cgroup '%s', empty affinity requested" % cgroup)
			return
		path = "%s/%s/%s" % (self._cgroup_mount_point, cgroup, "cpuset.cpus")
		if backup:
			orig_affinity = self._cmd.read_file(path, err_ret = "ERR", no_error = True).strip()
			if orig_affinity != "ERR":
				self._cgroups_original_affinity[cgroup] = orig_affinity
			else:
				log.error("Refusing to set affinity of cgroup '%s', reading original affinity failed" % cgroup)
				return
		if not self._cmd.write_to_file(path, affinity, no_error = True):
			log.error("Unable to set affinity '%s' for cgroup '%s'" % (affinity, cgroup))

	def _cgroup_set_affinity(self):
		if self._cgroup_affinity_initialized:
			return
		log.debug("Setting cgroups affinities")
		if self._affinity is not None and self._cgroup is not None and not self._cgroup in self._cgroups:
			self._cgroup_set_affinity_one(self._cgroup, self._affinity, backup = True)
		for cg in self._cgroups.items():
			self._cgroup_set_affinity_one(cg[0], cg[1], backup = True)
		self._cgroup_affinity_initialized = True

	def _cgroup_restore_affinity(self):
		log.debug("Restoring cgroups affinities")
		for cg in self._cgroups_original_affinity.items():
			self._cgroup_set_affinity_one(cg[0], cg[1])

	def _instance_apply_static(self, instance):
		# need to get "cgroup_mount_point_init", "cgroup_mount_point", "cgroup_groups_init",
		# "cgroup", and initialize mount point and cgroups before super class implementation call
		self._cgroup_mount_point = self._variables.expand(instance.options["cgroup_mount_point"])
		self._cgroup_mount_point_init = self._cmd.get_bool(self._variables.expand(
			instance.options["cgroup_mount_point_init"])) == "1"
		self._cgroup_groups_init = self._cmd.get_bool(self._variables.expand(
			instance.options["cgroup_groups_init"])) == "1"
		self._cgroup = self._sanitize_cgroup_path(self._variables.expand(
			instance.options["cgroup_for_isolated_cores"]))

		if self._cgroup_mount_point_init:
			self._cgroup_initialize()
		if self._cgroup_groups_init or self._cgroup_mount_point_init:
			self._cgroup_initialize_groups()

		super(SchedulerPlugin, self)._instance_apply_static(instance)

		self._cgroup_set_affinity()
		try:
			ps = self.get_processes()
		except (OSError, IOError) as e:
			log.error("error applying tuning, cannot get information about running processes: %s"
					% e)
			return
		sched_cfg = [(option, str(value).split(":", 4)) for option, value in instance._scheduler.items()]
		buf = [(option, self._convert_sched_cfg(vals))
				for option, vals in sched_cfg
				if re.match(r"group\.", option)
				and len(vals) == 5]
		sched_cfg = sorted(buf, key=lambda option_vals: option_vals[1][0])
		sched_all = dict()
		# for runtime tuning
		instance._sched_lookup = {}
		for option, (rule_prio, scheduler, priority, affinity, regex) \
				in sched_cfg:
			try:
				r = re.compile(regex)
			except re.error as e:
				log.error("error compiling regular expression: '%s'" % str(regex))
				continue
			processes = [(pid, cmd) for pid, cmd in ps.items() if re.search(r, cmd) is not None]
			#cmd - process name, option - group name
			sched = dict([(pid, (cmd, option, scheduler, priority, affinity, regex))
					for pid, cmd in processes])
			sched_all.update(sched)
			# make any contained regexes non-capturing: replace "(" with "(?:",
			# unless the "(" is preceded by "\" or followed by "?"
			regex = re.sub(r"(?<!\\)\((?!\?)", "(?:", str(regex))
			instance._sched_lookup[regex] = [scheduler, priority, affinity]
		for pid, (cmd, option, scheduler, priority, affinity, regex) \
				in sched_all.items():
			self._tune_process(pid, cmd, scheduler,
					priority, affinity)
		self._storage.set(self._scheduler_storage_key,
				self._scheduler_original)
		if self._daemon and instance._runtime_tuning:
			instance._thread = threading.Thread(target = self._thread_code, args = [instance])
			instance._thread.start()

	def _restore_ps_affinity(self):
		try:
			ps = self.get_processes()
		except (OSError, IOError) as e:
			log.error("error unapplying tuning, cannot get information about running processes: %s"
					% e)
			return
		for pid, orig_params in self._scheduler_original.items():
			# if command line for the pid didn't change, it's very probably the same process
			if pid not in ps or ps[pid] != orig_params.cmdline:
				continue
			if orig_params.scheduler is not None \
					and orig_params.priority is not None:
				self._set_rt(pid, orig_params.scheduler,
						orig_params.priority)
			if orig_params.cgroup is not None:
				self._set_cgroup(pid, orig_params.cgroup)
			elif orig_params.affinity is not None:
				self._set_affinity(pid, orig_params.affinity)
		self._scheduler_original = {}
		self._storage.unset(self._scheduler_storage_key)

	def _cgroup_cleanup_tasks_one(self, cgroup):
		cnt = int(consts.CGROUP_CLEANUP_TASKS_RETRY)
		data = " "
		while data != "" and cnt > 0:
			data = self._cmd.read_file("%s/%s/%s" % (self._cgroup_mount_point, cgroup, "tasks"),
				err_ret = " ", no_error = True)
			if data not in ["", " "]:
				for l in data.split("\n"):
					self._cmd.write_to_file("%s/%s" % (self._cgroup_mount_point, "tasks"), l, no_error = True)
			cnt -= 1
		if cnt == 0:
			log.warning("Unable to cleanup tasks from cgroup '%s'" % cgroup)

	def _cgroup_cleanup_tasks(self):
		if self._cgroup is not None and not self._cgroup in self._cgroups:
			self._cgroup_cleanup_tasks_one(self._cgroup)
		for cg in self._cgroups:
			self._cgroup_cleanup_tasks_one(cg)

	def _instance_unapply_static(self, instance, rollback = consts.ROLLBACK_SOFT):
		super(SchedulerPlugin, self)._instance_unapply_static(instance, rollback)
		if self._daemon and instance._runtime_tuning:
			instance._terminate.set()
			instance._thread.join()
		self._restore_ps_affinity()
		self._cgroup_restore_affinity()
		self._cgroup_cleanup_tasks()
		if self._cgroup_groups_init or self._cgroup_mount_point_init:
			self._cgroup_finalize_groups()
		if self._cgroup_mount_point_init:
			self._cgroup_finalize()

	def _cgroup_verify_affinity_one(self, cgroup, affinity):
		log.debug("Verifying cgroup '%s' affinity" % cgroup)
		path = "%s/%s/%s" % (self._cgroup_mount_point, cgroup, "cpuset.cpus")
		current_affinity = self._cmd.read_file(path, err_ret = "ERR", no_error = True)
		if current_affinity == "ERR":
			return True
		current_affinity = self._cmd.cpulist2string(self._cmd.cpulist_pack(current_affinity))
		affinity = self._cmd.cpulist2string(self._cmd.cpulist_pack(affinity))
		affinity_description = "cgroup '%s' affinity" % cgroup
		if current_affinity == affinity:
			log.info(consts.STR_VERIFY_PROFILE_VALUE_OK
					% (affinity_description, current_affinity))
			return True
		else:
			log.error(consts.STR_VERIFY_PROFILE_VALUE_FAIL
					% (affinity_description, current_affinity,
					affinity))
			return False

	def _cgroup_verify_affinity(self):
		log.debug("Veryfying cgroups affinities")
		ret = True
		if self._affinity is not None and self._cgroup is not None and not self._cgroup in self._cgroups:
			ret = ret and self._cgroup_verify_affinity_one(self._cgroup, self._affinity)
		for cg in self._cgroups.items():
			ret = ret and self._cgroup_verify_affinity_one(cg[0], cg[1])
		return ret

	def _instance_verify_static(self, instance, ignore_missing, devices):
		ret1 = super(SchedulerPlugin, self)._instance_verify_static(instance, ignore_missing, devices)
		ret2 = self._cgroup_verify_affinity()
		return ret1 and ret2

	def _add_pid(self, instance, pid, r):
		try:
			cmd = self._get_cmdline(pid)
		except (OSError, IOError) as e:
			if e.errno == errno.ENOENT \
					or e.errno == errno.ESRCH:
				log.debug("Failed to get cmdline of PID %d, the task vanished."
						% pid)
			else:
				log.error("Failed to get cmdline of PID %d: %s"
						% (pid, e))
			return
		v = self._cmd.re_lookup(instance._sched_lookup, cmd, r)
		if v is not None and not pid in self._scheduler_original:
			log.debug("tuning new process '%s' with PID '%d' by '%s'" % (cmd, pid, str(v)))
			(sched, prio, affinity) = v
			self._tune_process(pid, cmd, sched, prio,
					affinity)
			self._storage.set(self._scheduler_storage_key,
					self._scheduler_original)

	def _remove_pid(self, instance, pid):
		if pid in self._scheduler_original:
			del self._scheduler_original[pid]
			log.debug("removed PID %d from the rollback database" % pid)
			self._storage.set(self._scheduler_storage_key,
					self._scheduler_original)

	def _thread_code(self, instance):
		r = self._cmd.re_lookup_compile(instance._sched_lookup)
		poll = select.poll()
		# Store the file objects in a local variable so that they don't
		# go out of scope too soon. This is a workaround for
		# python3-perf bug rhbz#1659445.
		fds = instance._evlist.get_pollfd()
		for fd in fds:
			poll.register(fd)
		while not instance._terminate.is_set():
			# timeout to poll in milliseconds
			if len(poll.poll(self._sleep_interval * 1000)) > 0 and not instance._terminate.is_set():
				read_events = True
				while read_events:
					read_events = False
					for cpu in self._cpus:
						event = instance._evlist.read_on_cpu(cpu)
						if event:
							read_events = True
							if event.type == perf.RECORD_COMM or \
								(self._perf_process_fork_value and event.type == perf.RECORD_FORK):
								self._add_pid(instance, int(event.tid), r)
							elif event.type == perf.RECORD_EXIT:
								self._remove_pid(instance, int(event.tid))

	@command_custom("cgroup_ps_blacklist", per_device = False)
	def _cgroup_ps_blacklist(self, enabling, value, verify, ignore_missing):
		# currently unsupported
		if verify:
			return None
		if enabling and value is not None:
			self._cgroup_ps_blacklist_re = "|".join(["(%s)" % v for v in re.split(r"(?<!\\);", str(value))])

	@command_custom("ps_whitelist", per_device = False)
	def _ps_whitelist(self, enabling, value, verify, ignore_missing):
		# currently unsupported
		if verify:
			return None
		if enabling and value is not None:
			self._ps_whitelist = "|".join(["(%s)" % v for v in re.split(r"(?<!\\);", str(value))])

	@command_custom("ps_blacklist", per_device = False)
	def _ps_blacklist(self, enabling, value, verify, ignore_missing):
		# currently unsupported
		if verify:
			return None
		if enabling and value is not None:
			self._ps_blacklist = "|".join(["(%s)" % v for v in re.split(r"(?<!\\);", str(value))])

	@command_custom("irq_process", per_device = False)
	def _irq_process(self, enabling, value, verify, ignore_missing):
		# currently unsupported
		if verify:
			return None
		if enabling and value is not None:
			self._irq_process = self._cmd.get_bool(value) == "1"

	@command_custom("default_irq_smp_affinity", per_device = False)
	def _default_irq_smp_affinity(self, enabling, value, verify, ignore_missing):
		# currently unsupported
		if verify:
			return None
		if enabling and value is not None:
			if value in ["calc", "ignore"]:
				self._default_irq_smp_affinity_value = value
			else:
				self._default_irq_smp_affinity_value = self._cmd.cpulist_unpack(value)

	@command_custom("perf_process_fork", per_device = False)
	def _perf_process_fork(self, enabling, value, verify, ignore_missing):
		# currently unsupported
		if verify:
			return None
		if enabling and value is not None:
			self._perf_process_fork_value = self._cmd.get_bool(value) == "1"

	# Raises OSError
	# Raises SystemError with old (pre-0.4) python-schedutils
	# instead of OSError
	# If PID doesn't exist, errno == ESRCH
	def _get_affinity(self, pid):
		res = self._scheduler_utils.get_affinity(pid)
		log.debug("Read affinity '%s' of PID %d" % (res, pid))
		return res

	def _set_affinity(self, pid, affinity):
		log.debug("Setting CPU affinity of PID %d to '%s'." % (pid, affinity))
		try:
			self._scheduler_utils.set_affinity(pid, affinity)
		# Workaround for old python-schedutils (pre-0.4) which
		# incorrectly raised SystemError instead of OSError
		except (SystemError, OSError) as e:
			if not self._ignore_set_affinity_error(pid):
				log.error("Failed to set affinity of PID %d to '%s': %s"
						% (pid, affinity, e))

	# returns intersection of affinity1 with affinity2, if intersection is empty it returns affinity3
	def _get_intersect_affinity(self, affinity1, affinity2, affinity3):
		aff = set(affinity1).intersection(set(affinity2))
		if aff:
			return list(aff)
		return affinity3

	def _set_all_obj_affinity(self, objs, affinity, threads = False):
		psl = [v for v in objs if re.search(self._ps_whitelist,
				self._get_stat_comm(v)) is not None]
		if self._ps_blacklist != "":
			psl = [v for v in psl if re.search(self._ps_blacklist,
					self._get_stat_comm(v)) is None]
		if self._cgroup_ps_blacklist_re != "":
			psl = [v for v in psl if re.search(self._cgroup_ps_blacklist_re,
					self._get_stat_cgroup(v)) is None]
		psd = dict([(v.pid, v) for v in psl])
		for pid in psd:
			try:
				cmd = self._get_cmdline(psd[pid])
			except (OSError, IOError) as e:
				if e.errno == errno.ENOENT \
						or e.errno == errno.ESRCH:
					log.debug("Failed to get cmdline of PID %d, the task vanished."
							% pid)
				else:
					log.error("Refusing to set affinity of PID %d, failed to get its cmdline: %s"
							% (pid, e))
				continue
			cont = self._tune_process_affinity(pid, affinity,
					intersect = True)
			if not cont:
				continue
			if pid in self._scheduler_original:
				self._scheduler_original[pid].cmdline = cmd
			# process threads
			if not threads and "threads" in psd[pid]:
				self._set_all_obj_affinity(
						psd[pid]["threads"].values(),
						affinity, True)

	def _get_stat_cgroup(self, o):
		try:
			return o["cgroups"]
		except (OSError, IOError, KeyError):
			return ""

	def _get_stat_comm(self, o):
		try:
			return o["stat"]["comm"]
		except (OSError, IOError, KeyError):
			return ""

	def _set_ps_affinity(self, affinity):
		try:
			ps = procfs.pidstats()
			ps.reload_threads()
			self._set_all_obj_affinity(ps.values(), affinity, False)
		except (OSError, IOError) as e:
			log.error("error applying tuning, cannot get information about running processes: %s"
					% e)

	# Returns 0 on success, -2 if changing the affinity is not
	# supported, -1 if some other error occurs.
	def _set_irq_affinity(self, irq, affinity, restoring):
		try:
			affinity_hex = self._cmd.cpulist2hex(affinity)
			log.debug("Setting SMP affinity of IRQ %s to '%s'"
					% (irq, affinity_hex))
			filename = "/proc/irq/%s/smp_affinity" % irq
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

	def _set_default_irq_affinity(self, affinity):
		try:
			affinity_hex = self._cmd.cpulist2hex(affinity)
			log.debug("Setting default SMP IRQ affinity to '%s'"
					% affinity_hex)
			with open("/proc/irq/default_smp_affinity", "w") as f:
				f.write(affinity_hex)
		except (OSError, IOError) as e:
			log.error("Failed to set default SMP IRQ affinity to '%s': %s"
					% (affinity_hex, e))

	def _set_all_irq_affinity(self, affinity):
		irq_original = IRQAffinities()
		irqs = procfs.interrupts()
		for irq in irqs.keys():
			try:
				prev_affinity = irqs[irq]["affinity"]
				log.debug("Read affinity of IRQ '%s': '%s'"
						% (irq, prev_affinity))
			except KeyError:
				continue
			_affinity = self._get_intersect_affinity(prev_affinity, affinity, affinity)
			if set(_affinity) == set(prev_affinity):
				continue
			res = self._set_irq_affinity(irq, _affinity, False)
			if res == 0:
				irq_original.irqs[irq] = prev_affinity
			elif res == -2:
				irq_original.unchangeable.append(irq)

		# default affinity
		prev_affinity_hex = self._cmd.read_file("/proc/irq/default_smp_affinity")
		prev_affinity = self._cmd.hex2cpulist(prev_affinity_hex)
		if self._default_irq_smp_affinity_value == "calc":
			_affinity = self._get_intersect_affinity(prev_affinity, affinity, affinity)
		elif self._default_irq_smp_affinity_value != "ignore":
			_affinity = self._default_irq_smp_affinity_value
		if self._default_irq_smp_affinity_value != "ignore":
			self._set_default_irq_affinity(_affinity)
			irq_original.default = prev_affinity
		self._storage.set(self._irq_storage_key, irq_original)

	def _restore_all_irq_affinity(self):
		irq_original = self._storage.get(self._irq_storage_key, None)
		if irq_original is None:
			return
		for irq, affinity in irq_original.irqs.items():
			self._set_irq_affinity(irq, affinity, True)
		if self._default_irq_smp_affinity_value != "ignore":
			affinity = irq_original.default
			self._set_default_irq_affinity(affinity)
		self._storage.unset(self._irq_storage_key)

	def _verify_irq_affinity(self, irq_description, correct_affinity,
			current_affinity):
		res = set(current_affinity).issubset(set(correct_affinity))
		if res:
			log.info(consts.STR_VERIFY_PROFILE_VALUE_OK
					% (irq_description, current_affinity))
		else:
			log.error(consts.STR_VERIFY_PROFILE_VALUE_FAIL
					% (irq_description, current_affinity,
					correct_affinity))
		return res

	def _verify_all_irq_affinity(self, correct_affinity, ignore_missing):
		irq_original = self._storage.get(self._irq_storage_key, None)
		irqs = procfs.interrupts()
		res = True
		for irq in irqs.keys():
			if irq in irq_original.unchangeable and ignore_missing:
				description = "IRQ %s does not support changing SMP affinity" % irq
				log.info(consts.STR_VERIFY_PROFILE_VALUE_MISSING % description)
				continue
			try:
				current_affinity = irqs[irq]["affinity"]
				log.debug("Read SMP affinity of IRQ '%s': '%s'"
						% (irq, current_affinity))
				irq_description = "SMP affinity of IRQ %s" % irq
				if not self._verify_irq_affinity(
						irq_description,
						correct_affinity,
						current_affinity):
					res = False
			except KeyError:
				continue

		current_affinity_hex = self._cmd.read_file(
				"/proc/irq/default_smp_affinity")
		current_affinity = self._cmd.hex2cpulist(current_affinity_hex)
		if self._default_irq_smp_affinity_value != "ignore" and not self._verify_irq_affinity("default IRQ SMP affinity",
				current_affinity, correct_affinity if self._default_irq_smp_affinity_value == "calc" else
				self._default_irq_smp_affinity_value):
			res = False
		return res

	@command_custom("isolated_cores", per_device = False, priority = 10)
	def _isolated_cores(self, enabling, value, verify, ignore_missing):
		affinity = None
		self._affinity = None
		if value is not None:
			isolated = set(self._cmd.cpulist_unpack(value))
			present = set(self._cpus)
			if isolated.issubset(present):
				affinity = list(present - isolated)
				self._affinity = self._cmd.cpulist2string(affinity)
			else:
				str_cpus = self._cmd.cpulist2string(self._cpus)
				log.error("Invalid isolated_cores specified, '%s' does not match available cores '%s'"
						% (value, str_cpus))
		if (enabling or verify) and affinity is None:
			return None
		# currently only IRQ affinity verification is supported
		if verify:
			if self._irq_process:
				return self._verify_all_irq_affinity(affinity, ignore_missing)
			return True
		elif enabling:
			if self._cgroup:
				self._cgroup_set_affinity()
				ps_affinity = "cgroup.%s" % self._cgroup
			else:
				ps_affinity = affinity
			self._set_ps_affinity(ps_affinity)
			if self._irq_process:
				self._set_all_irq_affinity(affinity)
		else:
			# Restoring processes' affinity is done in
			# _instance_unapply_static()
			if self._irq_process:
				self._restore_all_irq_affinity()

	def _get_sched_knob_path(self, prefix, namespace, knob):
		key = "%s_%s_%s" % (prefix, namespace, knob)
		path = self._sched_knob_paths_cache.get(key)
		if path:
			return path
		path = "/proc/sys/kernel/%s_%s" % (namespace, knob)
		if not os.path.exists(path):
			if prefix == "":
				path = "%s/%s" % (namespace, knob)
			else:
				path = "%s/%s/%s" % (prefix, namespace, knob)
			path = "/sys/kernel/debug/%s" % path
			if self._secure_boot_hint is None:
				self._secure_boot_hint = True
		self._sched_knob_paths_cache[key] = path
		return path

	def _get_sched_knob(self, prefix, namespace, knob):
		data = self._cmd.read_file(self._get_sched_knob_path(prefix, namespace, knob), err_ret = None)
		if data is None:
			log.error("Error reading '%s'" % knob)
			if self._secure_boot_hint:
				log.error("This may not work with Secure Boot or kernel_lockdown (this hint is logged only once)")
				self._secure_boot_hint = False
		return data

	def _set_sched_knob(self, prefix, namespace, knob, value, sim, remove = False):
		if value is None:
			return None
		if not sim:
			if not self._cmd.write_to_file(self._get_sched_knob_path(prefix, namespace, knob), value, \
				no_error = [errno.ENOENT] if remove else False):
					log.error("Error writing value '%s' to '%s'" % (value, knob))
		return value

	@command_get("sched_min_granularity_ns")
	def _get_sched_min_granularity_ns(self):
		return self._get_sched_knob("", "sched", "min_granularity_ns")

	@command_set("sched_min_granularity_ns")
	def _set_sched_min_granularity_ns(self, value, sim, remove):
		return self._set_sched_knob("", "sched", "min_granularity_ns", value, sim, remove)

	@command_get("sched_latency_ns")
	def _get_sched_latency_ns(self):
		return self._get_sched_knob("", "sched", "latency_ns")

	@command_set("sched_latency_ns")
	def _set_sched_latency_ns(self, value, sim, remove):
		return self._set_sched_knob("", "sched", "latency_ns", value, sim, remove)

	@command_get("sched_wakeup_granularity_ns")
	def _get_sched_wakeup_granularity_ns(self):
		return self._get_sched_knob("", "sched", "wakeup_granularity_ns")

	@command_set("sched_wakeup_granularity_ns")
	def _set_sched_wakeup_granularity_ns(self, value, sim, remove):
		return self._set_sched_knob("", "sched", "wakeup_granularity_ns", value, sim, remove)

	@command_get("sched_tunable_scaling")
	def _get_sched_tunable_scaling(self):
		return self._get_sched_knob("", "sched", "tunable_scaling")

	@command_set("sched_tunable_scaling")
	def _set_sched_tunable_scaling(self, value, sim, remove):
		return self._set_sched_knob("", "sched", "tunable_scaling", value, sim, remove)

	@command_get("sched_migration_cost_ns")
	def _get_sched_migration_cost_ns(self):
		return self._get_sched_knob("", "sched", "migration_cost_ns")

	@command_set("sched_migration_cost_ns")
	def _set_sched_migration_cost_ns(self, value, sim, remove):
		return self._set_sched_knob("", "sched", "migration_cost_ns", value, sim, remove)

	@command_get("sched_nr_migrate")
	def _get_sched_nr_migrate(self):
		return self._get_sched_knob("", "sched", "nr_migrate")

	@command_set("sched_nr_migrate")
	def _set_sched_nr_migrate(self, value, sim, remove):
		return self._set_sched_knob("", "sched", "nr_migrate", value, sim, remove)

	@command_get("numa_balancing_scan_delay_ms")
	def _get_numa_balancing_scan_delay_ms(self):
		return self._get_sched_knob("sched", "numa_balancing", "scan_delay_ms")

	@command_set("numa_balancing_scan_delay_ms")
	def _set_numa_balancing_scan_delay_ms(self, value, sim, remove):
		return self._set_sched_knob("sched", "numa_balancing", "scan_delay_ms", value, sim, remove)

	@command_get("numa_balancing_scan_period_min_ms")
	def _get_numa_balancing_scan_period_min_ms(self):
		return self._get_sched_knob("sched", "numa_balancing", "scan_period_min_ms")

	@command_set("numa_balancing_scan_period_min_ms")
	def _set_numa_balancing_scan_period_min_ms(self, value, sim, remove):
		return self._set_sched_knob("sched", "numa_balancing", "scan_period_min_ms", value, sim, remove)

	@command_get("numa_balancing_scan_period_max_ms")
	def _get_numa_balancing_scan_period_max_ms(self):
		return self._get_sched_knob("sched", "numa_balancing", "scan_period_max_ms")

	@command_set("numa_balancing_scan_period_max_ms")
	def _set_numa_balancing_scan_period_max_ms(self, value, sim, remove):
		return self._set_sched_knob("sched", "numa_balancing", "scan_period_max_ms", value, sim, remove)

	@command_get("numa_balancing_scan_size_mb")
	def _get_numa_balancing_scan_size_mb(self):
		return self._get_sched_knob("sched", "numa_balancing", "scan_size_mb")

	@command_set("numa_balancing_scan_size_mb")
	def _set_numa_balancing_scan_size_mb(self, value, sim, remove):
		return self._set_sched_knob("sched", "numa_balancing", "scan_size_mb", value, sim, remove)
