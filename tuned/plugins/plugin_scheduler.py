# code for cores isolation was inspired by Tuna implementation
# perf code was borrowed from kernel/tools/perf/python/twatch.py
# thanks to Arnaldo Carvalho de Melo <acme@redhat.com>

import base
from decorators import *
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
import errno

log = tuned.logs.get()

# TODO move from cmdline tools to schedutils and consolidate the code
class SchedulerPlugin(base.Plugin):
	"""
	Plugin for tuning of scheduler. Currently it can control scheduling
	priorities of system threads (it is substitution for the rtctl tool).
	"""

	_dict_sched2param = {"SCHED_FIFO":"f", "SCHED_BATCH":"b", "SCHED_RR":"r",
		"SCHED_OTHER":"o", "SCHED_IDLE":"i"}

	def __init__(self, monitor_repository, storage_factory, hardware_inventory, device_matcher, device_matcher_udev, plugin_instance_factory, global_cfg, variables):
		super(self.__class__, self).__init__(monitor_repository, storage_factory, hardware_inventory, device_matcher, device_matcher_udev, plugin_instance_factory, global_cfg, variables)
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

	def _scheduler_storage_key(self, instance):
		return "%s/options" % instance.name

	def _instance_init(self, instance):
		instance._has_dynamic_tuning = False
		instance._has_static_tuning = True
		# this is hack, runtime_tuning should be covered by dynamic_tuning configuration
		# TODO: add per plugin dynamic tuning configuration and use dynamic_tuning configuration
		# instead of runtime_tuning
		instance._runtime_tuning = True

		# FIXME: do we want to do this here?
		# recover original values in case of crash
		instance._scheduler_original = self._storage.get(self._scheduler_storage_key(instance), {})
		if len(instance._scheduler_original) > 0:
			log.info("recovering scheduling settings from previous run")
			self._instance_unapply_static(instance)
			instance._scheduler_original = {}
			self._storage.unset(self._scheduler_storage_key(instance))

		instance._scheduler = instance.options
		for k in instance._scheduler:
			instance._scheduler[k] = self._variables.expand(instance._scheduler[k])
		if self._cmd.get_bool(instance._scheduler.get("runtime", 1)) == "0":
			instance._runtime_tuning = False
		instance._terminate = threading.Event()
		if self._daemon and instance._runtime_tuning:
			try:
				instance._cpus = perf.cpu_map()
				instance._threads = perf.thread_map()
				evsel = perf.evsel(type = perf.TYPE_SOFTWARE,
					config = perf.COUNT_SW_DUMMY,
					task = 1, comm = 1, mmap = 0, freq = 0,
					wakeup_events = 1, watermark = 1,
					sample_type = perf.SAMPLE_TID | perf.SAMPLE_CPU)
				evsel.open(cpus = instance._cpus, threads = instance._threads)
				instance._evlist = perf.evlist(instance._cpus, instance._threads)
				instance._evlist.add(evsel)
				instance._evlist.mmap()
			# no perf
			except:
				instance._runtime_tuning = False

	def _instance_cleanup(self, instance):
		pass

	@classmethod
	def _get_config_options(cls):
		return {
			"isolated_cores":       None,
			"ps_whitelist": None,
			"ps_blacklist": None,
		}

	def get_process(self, pid):
		cmd = self._cmd.read_file("/proc/" + pid + "/comm", no_error = True)
		if cmd == "":
			return ""
		cmd = cmd.strip()
		cmdline = self._cmd.read_file("/proc/" + pid + "/cmdline", no_error = True)
		if cmdline == "":
			return "[" + cmd + "]"
		else:
			return cmdline.replace("\0", " ").strip()

	def get_processes(self):
		(rc, out) = self._cmd.execute(["ps", "-eopid,cmd", "--no-headers"])
		if rc != 0 or len(out) <= 0:
			return None
		return dict(map(lambda (pid, cmd): (int(pid.lstrip()), cmd.lstrip()),
			filter(lambda i: len(i) == 2, map(lambda s: s.split(None, 1), out.split("\n")))))

	def _parse_val(self, val):
		v = val.split(":", 1)
		if len(v) == 2:
			return v[1].strip()
		else:
			return None

	def _pid_exists(self, pid):
		try:
			p = procfs.pidstat(pid)
			return True
		except:
			return False

	def _get_rt(self, pid):
		(rc, out, err_msg) = self._cmd.execute(["chrt", "-p", str(pid)], return_err = True)
		if rc != 0:
			if self._pid_exists(pid):
				log.error(err_msg)
			else:
				log.debug("Unable to read scheduling parameters for PID %s, the task vanished." % pid)
			return None
		vals = out.split("\n", 1)
		if len(vals) > 1:
			sched = self._parse_val(vals[0])
			prio = self._parse_val(vals[1])
		else:
			sched = None
			prio = None
		log.debug("read scheduler policy '%s' and priority '%s' for pid '%s'" % (sched, prio, pid))
		return (sched, prio)

	def _get_affinity(self, pid, no_error = False):
		(rc, out, err_msg) = self._cmd.execute(["taskset", "-p", str(pid)], no_errors = [1] if no_error else [], return_err = True)
		if rc != 0:
			if rc != 1 or not no_error:
				if self._pid_exists(pid):
					log.error(err_msg)
				else:
					log.debug("Unable to read affinity for PID %s, the task vanished." % pid)
			return None
		v = self._parse_val(out.split("\n", 1)[0])
		log.debug("read affinity '%s' for pid '%s'" % (v, pid))
		return v

	def _schedcfg2param(self, sched):
		if sched in ["f", "b", "r", "o"]:
			return "-" + sched
		# including '*'
		else:
			return ""

	def _sched2param(self, sched):
		try:
			return "-" + self._dict_sched2param[sched]
		except KeyError:
			return ""

	def _set_rt(self, pid, sched, prio, no_error = False):
		if pid is None or prio is None:
			return
		if sched is not None and len(sched) > 0:
			schedl = [sched]
			log.debug("setting scheduler policy to '%s' for PID '%s'" % (sched,  pid))
		else:
			schedl = []
		log.debug("setting scheduler priority to '%s' for PID '%s'" % (prio, pid))
		(ret, out, err_msg) = self._cmd.execute(["chrt"] + schedl + ["-p", str(prio), str(pid)], no_errors = [1] if no_error else [], return_err = True)
		if ret == 0 or (ret == 1 and no_error):
			return
		if self._pid_exists(pid):
			log.error(err_msg)
		else:
			log.debug("Unable to set scheduling parameters for PID %s, the task vanished." % pid)

	# Return codes:
	# 0 - Affinity is fixed
	# 1 - Affinity is changeable
	# -1 - Task vanished
	# -2 - Error
	def _affinity_changeable(self, pid, process = None):
		try:
			if process is None:
				process = procfs.process(pid)
			if process["stat"].is_bound_to_cpu():
				if process["stat"]["state"] == "Z":
					log.debug("Affinity of zombie task with PID %s cannot be changed, the task's affinity mask is fixed." % pid)
				elif len(process["cmdline"]) == 0:
					log.debug("Affinity of kernel thread with PID %s cannot be changed, the task's affinity mask is fixed." % pid)
				else:
					log.warn("Affinity of task with PID %s cannot be changed, the task's affinity mask is fixed." % pid)
				return 0
			else:
				return 1
		except IOError as e:
			if e[0] == errno.ENOENT or e[0] == errno.ESRCH:
				log.debug("Unable to set affinity for PID %s, the task vanished." % pid)
				return -1
			else:
				log.error("Failed to get task info for PID %s: %s" % (pid, str(e)))
				return -2
		except (OSError, AttributeError, KeyError) as e:
			log.error("Failed to get task info for PID %s: %s" % (pid, str(e)))
			return -2

	def _set_affinity(self, pid, affinity, no_error = False):
		if pid is None or affinity is None:
			return
		log.debug("setting affinity to '%s' for PID '%s'" % (affinity, pid))
		(ret, out, err_msg) = self._cmd.execute(["taskset", "-p", str(affinity), str(pid)], no_errors = [1] if no_error else [], return_err = True)
		if ret == 0 or (ret == 1 and no_error):
			return
		res = self._affinity_changeable(pid)
		if res == 1 or res == -2:
			log.error(err_msg)

	#tune process and store previous values
	def _tune_process(self, instance, pid, cmd, sched, prio, affinity, no_error = False):
		#rt[0] - prev_sched, rt[1] - prev_prio
		rt = self._get_rt(pid)
		prev_affinity = self._get_affinity(pid, no_error)
		if prev_affinity is not None and rt is not None and len(rt) == 2 and rt[0] is not None and rt[1] is not None:
			instance._scheduler_original[pid] = (cmd, rt[0], rt[1], prev_affinity)
		self._set_rt(pid, self._schedcfg2param(sched), prio, no_error)
		if affinity != "*":
			self._set_affinity(pid, affinity, no_error)

	def _instance_apply_static(self, instance):
		super(self.__class__, self)._instance_apply_static(instance)
		ps = self.get_processes()
		if ps is None:
			log.error("error applying tuning, cannot get information about running processes")
			return
		instance._sched_cfg = map(lambda (option, value): (option, str(value).split(":", 4)), instance._scheduler.items())
		buf = filter(lambda (option, vals): re.match(r"group\.", option) and len(vals) == 5, instance._sched_cfg)
		instance._sched_cfg = sorted(buf, key=lambda (option, vals): vals[0])
		sched_all = dict()
		# for runtime tunning
		instance._sched_lookup = {}
		for option, vals in instance._sched_cfg:
			try:
				r = re.compile(vals[4])
			except re.error as e:
				log.error("error compiling regular expression: '%s'" % str(vals[4]))
				continue
			processes = filter(lambda (pid, cmd): re.search(r, cmd) is not None, ps.items())
			#cmd - process name, option - group name, vals[0] - rule prio, vals[1] - sched, vals[2] - prio,
			#vals[3] - affinity, vals[4] - regex
			sched = dict(map(lambda (pid, cmd): (pid, (cmd, option, vals[1], vals[2], vals[3], vals[4])), processes))
			sched_all.update(sched)
			v4 = str(vals[4]).replace("(", r"\(")
			v4 = v4.replace(")", r"\)")
			instance._sched_lookup[v4] = [vals[1], vals[2], vals[3]]
		for pid, vals in sched_all.items():
			#vals[0] - process name, vals[1] - rule prio, vals[2] - sched, vals[3] - prio, vals[4] - affinity,
			#vals[5] - regex
			self._tune_process(instance, pid, vals[0], vals[2], vals[3], vals[4])
		self._storage.set("options", instance._scheduler_original)
		if self._daemon and instance._runtime_tuning:
			instance._thread = threading.Thread(target = self._thread_code, args = [instance])
			instance._thread.start()

	def _instance_unapply_static(self, instance, full_rollback = False):
		super(self.__class__, self)._instance_unapply_static(instance, full_rollback)
		ps = self.get_processes()
		if self._daemon and instance._runtime_tuning:
			instance._terminate.set()
			instance._thread.join()

		for pid, vals in instance._scheduler_original.items():
			# if command line for the pid didn't change, it's very probably the same process
			try:
				if ps[pid] == vals[0]:
					self._set_rt(pid, self._sched2param(vals[1]), vals[2])
					self._set_affinity(pid, vals[3])
			except KeyError as e:
				pass

	def _add_pid(self, instance, pid, r):
		cmd = self.get_process(pid)
		# check to filter short living process
		if cmd == "":
			return
		v = self._cmd.re_lookup(instance._sched_lookup, cmd, r)
		if v is not None and not pid in instance._scheduler_original:
			log.debug("tuning new process '%s' with pid '%s' by '%s'" % (cmd, pid, str(v)))
			#v[0] - sched, v[1] - prio, v[2] - affinity
			self._tune_process(instance, pid, cmd, v[0], v[1], v[2], no_error = True)
			self._storage.set("options", instance._scheduler_original)

	def _remove_pid(self, instance, pid):
		if pid in instance._scheduler_original:
			del instance._scheduler_original[pid]
			log.debug("removed PID %s from the rollback database" % pid)
			self._storage.set("options", instance._scheduler_original)

	def _thread_code(self, instance):
		r = self._cmd.re_lookup_compile(instance._sched_lookup)
		poll = select.poll()
		for fd in instance._evlist.get_pollfd():
			poll.register(fd)
		while not instance._terminate.is_set():
			# timeout to poll in milliseconds
			if len(poll.poll(self._sleep_interval * 1000)) > 0 and not instance._terminate.is_set():
				read_events = True
				while read_events:
					read_events = False
					for cpu in instance._cpus:
						event = instance._evlist.read_on_cpu(cpu)
						if event:
							read_events = True
							if event.type == perf.RECORD_COMM:
								self._add_pid(instance, str(event.pid), r)
							elif event.type == perf.RECORD_EXIT:
								self._remove_pid(instance, str(event.pid))

	@command_custom("ps_whitelist", per_device = False)
	def _ps_whitelist(self, enabling, value, verify, ignore_missing):
		# currently unsupported
		if verify:
			return None
		if enabling and value is not None:
			self._ps_whitelist = "|".join(map(lambda v: "(%s)" % v, re.split(r"(?<!\\);", str(value))))

	@command_custom("ps_blacklist", per_device = False)
	def _ps_blacklist(self, enabling, value, verify, ignore_missing):
		# currently unsupported
		if verify:
			return None
		if enabling and value is not None:
			self._ps_blacklist = "|".join(map(lambda v: "(%s)" % v, re.split(r"(?<!\\);", str(value))))

	# TODO: merge with _get_affinity
	def _get_affinity2(self, pid):
		try:
			return schedutils.get_affinity(pid)
		# Workaround for old python-schedutils which incorrectly raised error
		except (SystemError, OSError) as e:
			if e[0] == 3:
				log.debug("Unable to read affinity for PID %s, the task vanished." % pid)
				return None
			log.error("unable to get affinity for PID '%s': %s" % (str(pid), e))
			return None

	# TODO: merge with _set_affinity
	def _set_affinity2(self, pid, affinity):
		try:
			schedutils.set_affinity(pid, affinity)
		# Workaround for old python-schedutils which incorrectly raised error
		except (SystemError, OSError) as e:
			if e[0] == 3:
				log.debug("Unable to set affinity for PID %s, the task vanished." % pid)
				return False
			log.error("unable to set affinity '%s' for PID '%s': %s" % (str(affinity), str(pid), e))
			return False
		return True

	# returns intersection of affinity1 with affinity2, if intersection is empty it returns affinity3
	def _get_intersect_affinity(self, affinity1, affinity2, affinity3):
		aff = set(affinity1).intersection(set(affinity2))
		if aff:
			return list(aff)
		return affinity3

	def _set_all_obj_affinity(self, objs, affinity, threads = False, intersect = False):
		_affinity = affinity
		for obj in objs:
			if self._affinity_changeable(obj, process = objs[obj]) != 1:
				continue
			prev_affinity = self._get_affinity2(obj)
			if prev_affinity is None:
				continue
			if intersect:
				_affinity = self._get_intersect_affinity(prev_affinity, affinity, affinity)
			if set(_affinity) != set(prev_affinity):
				if not self._set_affinity2(obj, _affinity):
					continue
			# process threads
			if not threads and objs[obj].has_key("threads"):
				self._set_all_obj_affinity(dict(objs[obj]["threads"].items()), affinity, True, intersect)

	def _get_stat_comm(self, o):
		try:
			return o["stat"]["comm"]
		except (OSError, IOError, KeyError):
			return ""

	def _set_ps_affinity(self, affinity, intersect = False):
		_affinity = affinity
		affinity_hex = self._cmd.cpulist2hex(_affinity)
		ps = procfs.pidstats()
		ps.reload_threads()
		psl = filter(lambda v: re.search(self._ps_whitelist, self._get_stat_comm(v)) is not None, ps.values())
		if self._ps_blacklist != "":
			psl = filter(lambda v: re.search(self._ps_blacklist, self._get_stat_comm(v)) is None, psl)
		psd = dict(map(lambda v: (v.pid, v), psl))
		self._set_all_obj_affinity(psd, affinity, False, intersect)

		# process IRQs
		irqs = procfs.interrupts()
		for irq in irqs.keys():
			try:
				prev_affinity = irqs[irq]["affinity"]
			except KeyError:
				continue
			if intersect:
				_affinity = self._get_intersect_affinity(prev_affinity, affinity, affinity)
				affinity_hex = self._cmd.cpulist2hex(_affinity)
			self._cmd.write_to_file("/proc/irq/%s/smp_affinity" % irq, affinity_hex, no_error = True)

		# default affinity
		prev_affinity_hex = self._cmd.read_file("/proc/irq/default_smp_affinity")
		prev_affinity = self._cmd.hex2cpulist(prev_affinity_hex)
		if intersect:
			_affinity = self._get_intersect_affinity(prev_affinity, affinity, affinity)
			affinity_hex = self._cmd.cpulist2hex(_affinity)
		self._cmd.write_to_file("/proc/irq/default_smp_affinity", affinity_hex)

	@command_custom("isolated_cores", per_device = False, priority = 10)
	def _isolated_cores(self, enabling, value, verify, ignore_missing):
		# currently unsupported
		if verify:
			return None
		# TODO merge with instance._cpus
		cpus = list(perf.cpu_map())
		if enabling:
			if value is not None:
				affinity = self._cmd.cpulist_invert(value)
				sa = set(affinity)
				if set(cpus).intersection(sa) != sa:
					log.error("invalid isolated_cores specified, '%s' don't match available cores '%s'" % (value, ",".cpus))
					return None
				self._set_ps_affinity(affinity, True)
		else:
			self._set_ps_affinity(cpus, False)
