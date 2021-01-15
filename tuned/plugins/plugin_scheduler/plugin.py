# code for cores isolation was inspired by Tuna implementation
# perf code was borrowed from kernel/tools/perf/python/twatch.py
# thanks to Arnaldo Carvalho de Melo <acme@redhat.com>

from tuned.plugins import base
from tuned.plugins.decorators import *
import tuned.logs
import re
from subprocess import *
import threading
import perf
import select
import tuned.consts as consts
import procfs
import schedutils
from tuned.utils.commands import commands
from tuned.utils.file import FileHandler
import errno
import os
import collections
import math

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

class SchedulerPlugin(base.Plugin):
	"""
	Plugin for tuning of scheduler. Currently it can control scheduling
	priorities of system threads (it is substitution for the rtctl tool).
	"""

	_dict_schedcfg2num = {
			"f": schedutils.SCHED_FIFO,
			"b": schedutils.SCHED_BATCH,
			"r": schedutils.SCHED_RR,
			"o": schedutils.SCHED_OTHER,
			"i": schedutils.SCHED_IDLE,
			}

	def __init__(self, monitor_repository, storage_factory, hardware_inventory, device_matcher, device_matcher_udev, plugin_instance_factory, global_cfg, variables):
		super(SchedulerPlugin, self).__init__(monitor_repository, storage_factory, hardware_inventory, device_matcher, device_matcher_udev, plugin_instance_factory, global_cfg, variables)
		self._has_dynamic_options = True
		self._daemon = consts.CFG_DEF_DAEMON
		self._sleep_interval = int(consts.CFG_DEF_SLEEP_INTERVAL)
		if global_cfg is not None:
			self._daemon = global_cfg.get_bool(consts.CFG_DAEMON, consts.CFG_DEF_DAEMON)
			self._sleep_interval = int(global_cfg.get(consts.CFG_SLEEP_INTERVAL, consts.CFG_DEF_SLEEP_INTERVAL))
		self._cmd = commands()
		# default is to whitelist all and blacklist none
		self._ps_whitelist = ".*"
		self._ps_blacklist = ""
		self._cpus = perf.cpu_map()
		self._scheduler_storage_key = self._storage_key(
				command_name = "scheduler")
		self._irq_storage_key = self._storage_key(
				command_name = "irq")
		self._file_handler = FileHandler(log_func = log.debug)

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
		pass

	@classmethod
	def _get_config_options(cls):
		return {
			"isolated_cores": None,
			"cgroup_mount_point": consts.DEF_CGROUP_MOUNT_POINT,
			"cgroup_mount_point_init": False,
			"cgroup_groups_init": True,
			"cgroup_for_isolated_cores": None,
			"ps_whitelist": None,
			"ps_blacklist": None,
			"default_irq_smp_affinity": "calc",
			"perf_mmap_pages": None,
			"perf_process_fork": "false",
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
		scheduler = schedutils.get_scheduler(pid)
		sched_str = schedutils.schedstr(scheduler)
		priority = schedutils.get_priority(pid)
		log.debug("Read scheduler policy '%s' and priority '%d' of PID '%d'"
				% (sched_str, priority, pid))
		return (scheduler, priority)

	def _set_rt(self, pid, sched, prio):
		sched_str = schedutils.schedstr(sched)
		log.debug("Setting scheduler policy to '%s' and priority to '%d' of PID '%d'."
				% (sched_str, prio, pid))
		try:
			prio_min = schedutils.get_priority_min(sched)
			prio_max = schedutils.get_priority_max(sched)
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
			schedutils.set_scheduler(pid, sched, prio)
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

	# Return codes:
	# 0 - Affinity is fixed
	# 1 - Affinity is changeable
	# -1 - Task vanished
	# -2 - Error
	def _affinity_changeable(self, pid):
		try:
			process = procfs.process(pid)
			if process["stat"].is_bound_to_cpu():
				if process["stat"]["state"] == "Z":
					log.debug("Affinity of zombie task with PID %d cannot be changed, the task's affinity mask is fixed."
							% pid)
				elif self._is_kthread(process):
					log.debug("Affinity of kernel thread with PID %d cannot be changed, the task's affinity mask is fixed."
							% pid)
				else:
					log.warn("Affinity of task with PID %d cannot be changed, the task's affinity mask is fixed."
							% pid)
				return 0
			else:
				return 1
		except (OSError, IOError) as e:
			if e.errno == errno.ENOENT or e.errno == errno.ESRCH:
				log.debug("Failed to get task info for PID %d, the task vanished."
						% pid)
				return -1
			else:
				log.error("Failed to get task info for PID %d: %s"
						% (pid, e))
				return -2
		except (AttributeError, KeyError) as e:
			log.error("Failed to get task info for PID %d: %s"
					% (pid, e))
			return -2

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
		scheduler = self._dict_schedcfg2num.get(str_scheduler)
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
				log.err("Refusing to set affinity of cgroup '%s', reading original affinity failed" % cgroup)
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
		# for runtime tunning
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
			regex = str(regex).replace("(", r"\(")
			regex = regex.replace(")", r"\)")
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
			log.warn("Unable to cleanup tasks from cgroup '%s'" % cgroup)

	def _cgroup_cleanup_tasks(self):
		if self._cgroup is not None and not self._cgroup in self._cgroups:
			self._cgroup_cleanup_tasks_one(self._cgroup)
		for cg in self._cgroups:
			self._cgroup_cleanup_tasks_one(cg)

	def _instance_unapply_static(self, instance, full_rollback = False):
		super(SchedulerPlugin, self)._instance_unapply_static(instance, full_rollback)
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
		res = schedutils.get_affinity(pid)
		log.debug("Read affinity '%s' of PID %d" % (res, pid))
		return res

	def _set_affinity(self, pid, affinity):
		log.debug("Setting CPU affinity of PID %d to '%s'." % (pid, affinity))
		try:
			schedutils.set_affinity(pid, affinity)
			return True
		# Workaround for old python-schedutils (pre-0.4) which
		# incorrectly raised SystemError instead of OSError
		except (SystemError, OSError) as e:
			if hasattr(e, "errno") and e.errno == errno.ESRCH:
				log.debug("Failed to set affinity of PID %d, the task vanished."
						% pid)
			else:
				res = self._affinity_changeable(pid)
				if res == 1 or res == -2:
					log.error("Failed to set affinity of PID %d to '%s': %s"
							% (pid, affinity, e))
			return False

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
			self._file_handler.write(filename, affinity_hex)
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
			path = "/proc/irq/default_smp_affinity"
			self._file_handler.write(path, affinity_hex)
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
			return self._verify_all_irq_affinity(affinity, ignore_missing)
		elif enabling:
			if self._cgroup:
				self._cgroup_set_affinity()
				ps_affinity = "cgroup.%s" % self._cgroup
			else:
				ps_affinity = affinity
			self._set_ps_affinity(ps_affinity)
			self._set_all_irq_affinity(affinity)
		else:
			# Restoring processes' affinity is done in
			# _instance_unapply_static()
			self._restore_all_irq_affinity()
