import base
from decorators import *
import tuned.logs
import re
from subprocess import *
from tuned.utils.commands import commands

log = tuned.logs.get()

class SchedulerPlugin(base.Plugin):
	"""
	Plugin for tuning of scheduler. Currently it can control scheduling
	priorities of system threads (it is substitution for the rtctl tool).
	"""

	_dict_sched2param = {"SCHED_FIFO":"f", "SCHED_BATCH":"b", "SCHED_RR":"r",
		"SCHED_OTHER":"o", "SCHED_IDLE":"i"}

	def __init__(self, *args, **kwargs):
		super(self.__class__, self).__init__(*args, **kwargs)
		self._has_dynamic_options = True
		self._cmd = commands()

	def _scheduler_storage_key(self, instance):
		return "%s/options" % instance.name

	def _instance_init(self, instance):
		instance._has_dynamic_tuning = False
		instance._has_static_tuning = True

		# FIXME: do we want to do this here?
		# recover original values in case of crash
		instance._scheduler_original = self._storage.get(self._scheduler_storage_key(instance), {})
		if len(instance._scheduler_original) > 0:
			log.info("recovering scheduling settings from previous run")
			self._instance_unapply_static(instance)
			instance._scheduler_original = {}
			self._storage.unset(self._scheduler_storage_key(instance))

		instance._scheduler = instance.options

	def _instance_cleanup(self, instance):
		pass

	def get_processes(self):
		(rc, out) = self._cmd.execute(["ps", "-eopid,cmd", "--no-headers"])
		if rc != 0 or len(out) <= 0:
			return None
		return dict(map(lambda (pid, cmd): (pid.lstrip(), cmd.lstrip()),
			filter(lambda i: len(i) == 2, map(lambda s: s.split(None, 1), out.split("\n")))))

	def _parse_val(self, val):
		v = val.split(":", 1)
		if len(v) == 2:
			return v[1].strip()
		else:
			return None

	def _get_rt(self, pid):
		(rc, out) = self._cmd.execute(["chrt", "-p", str(pid)])
		if rc != 0:
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

	def _get_affinity(self, pid):
		(rc, out) = self._cmd.execute(["taskset", "-p", str(pid)])
		if rc != 0:
			return None
		v = self._parse_val(out.split("\n", 1)[0])
		log.debug("read affinity '%s' for pid '%s'" % (v, pid))
		return v

	def _schedcfg2param(self, sched):
		if sched in ["f", "b", "r", "o"]:
			return "-" + sched
		else:
			return ""

	def _sched2param(self, sched):
		try:
			return "-" + self._dict_sched2param[sched]
		except KeyError:
			return ""

	def _set_rt(self, pid, sched, prio):
		if pid is None or prio is None:
			return
		if sched is not None and len(sched) > 0:
			schedl = [sched]
			log.debug("setting scheduler policy to '%s' for PID '%s'" % (sched,  pid))
		else:
			schedl = []
		log.debug("setting scheduler priority to '%s' for PID '%s'" % (prio, pid))
		self._cmd.execute(["chrt"] + schedl + ["-p", str(prio), str(pid)])

	def _set_affinity(self, pid, affinity):
		if pid is None or affinity is None:
			return
		log.debug("setting affinity to '%s' for PID '%s'" % (affinity, pid))
		self._cmd.execute(["taskset", "-p", str(affinity), str(pid)])

	def _instance_apply_static(self, instance):
		ps = self.get_processes()
		if ps is None:
			log.error("error applying tuning, cannot get information about running processes")
			return
		for k in instance._scheduler:
			instance._scheduler[k] = self._variables.expand(instance._scheduler[k])
		sched_cfg = map(lambda (option, value): (option, value.split(":", 4)), instance._scheduler.items())
		buf = filter(lambda (option, vals): re.match(r"group\.", option) and len(vals) == 5, sched_cfg)
		sched_cfg = sorted(buf, key=lambda (option, vals): vals[0])
		sched_all = dict()
		for option, vals in sched_cfg:
			try:
				r = re.compile(vals[4])
			except re.error as e:
				log.error("error compiling regular expression: '%s'" % str(vals[4]))
				continue
			processes = filter(lambda (pid, cmd): re.search(r, cmd) is not None, ps.items())
			sched = dict(map(lambda (pid, cmd): (pid, (cmd, option, vals[1], vals[2], vals[3], vals[4])), processes))
			sched_all.update(sched)
		for pid, vals in sched_all.items():
			(sched, prio) = self._get_rt(pid)
			affinity = self._get_affinity(pid)
			if affinity is not None and sched is not None and prio is not None:
				instance._scheduler_original[pid] = (vals[0], sched, prio, affinity)
			self._set_rt(pid, self._schedcfg2param(vals[2]), vals[3])
			if vals[4] != "*":
				self._set_affinity(pid, vals[4])
		self._storage.set("options", instance._scheduler_original)

	def _instance_unapply_static(self, instance, profile_switch = False):
		ps = self.get_processes()
		for pid, vals in instance._scheduler_original.iteritems():
			# if command line for the pid didn't change, it's very probably the same process
			try:
				if ps[pid] == vals[0]:
					self._set_rt(pid, self._sched2param(vals[1]), vals[2])
					self._set_affinity(pid, vals[3])
			except KeyError as e:
				pass
