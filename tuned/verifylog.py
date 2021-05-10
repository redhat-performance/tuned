
import json

class VerifyLog:

	obj = None

	def __init__(self, log={}):
		self.vLog = log
		return

	@classmethod
	def get_obj(self, log={}):
		"""
		Create and return a singleton object.
		"""
		if (not self.obj):
			self.obj = VerifyLog(log)
		return self.obj

	def add_log(self, iname, log={}):
		if (iname not in self.vLog.keys()):
			self.vLog[iname] = []
		if (log):
			self.vLog[iname].append(log)

		return

	def get_log(self):
		return self.vLog

	def put_log(self):
		vlog = self.vLog
		self.vLog = {}
		return vlog

	def _display_device(self, log):
		ret = True
		for i in range(len(log)):
			for cmd in list(log[i].keys()):
				print(" %s=%s" % (cmd, log[i][cmd]["value"]))
				for dev in log[i][cmd]["devices"]:
					for k in dev.keys():
						cv = dev[k]["value"]
						rs = dev[k]["result"]
						print("  %s=%s" % (k, cv))
						if (ret):
							ret = rs
		return ret

	def _display_non_device(self, log):
		ret = True
		for i in range(len(log)):
			for opt in list(log[i].keys()):
				cv = log[i][opt]["value"]
				ev = log[i][opt]["expected"]
				rs = log[i][opt]["result"]
				print(" %s=%s"
					% (opt, cv), end="\n" if rs else ", ")
				if (not rs):
					print("[Expected: %s]" % ev)
					ret = rs
		return ret

	def _display_modules(self, log):
		ret = True
		for i in range(len(log)):
			m = list(log[i].keys())[0]
			mod = log[i][m]
			print(" %s: %s" % (m, mod["message"]))
			ret = mod["result"] if (ret) else False

		return ret

	def _display_net(self, log):
		ret = True
		for i in range(len(log)):
			for opt in list(log[i].keys()):
				if ("expected" in list(log[i][opt].keys())):
					rs = self._display_non_device([log[i]])
				elif ("devices" in list(log[i][opt].keys())):
					rs = self._display_device([log[i]])
				if (ret):
					ret = rs
		return ret


	def display(self):
		device_log = ["audio", "cpu", "disk", "scsi_host", "video"]
		non_device_log = ["bootloader", "eeepc_she", "irqbalance",
				"rtentst", "scheduler", "sysctl",
				"sysfs", "vm"]
		ret = True
		instances = json.loads(self.put_log())
		for key in instances.keys():
			print("[%s]" % key)
			if key in device_log:
				rs = self._display_device(instances[key])
			elif key in non_device_log:
				rs = self._display_non_device(instances[key])
			elif key in ["modules", "script"]:
				rs = self._display_modules(instances[key])
			elif key == "net":
				rs = self._display_net(instances[key])
			print("Verification: %s\n" % ("Pass" if rs else "Fail"))
			if ret:
				ret = rs
		return ret
