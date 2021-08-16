
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

	def add_log(self, iname, kname, current="",
                    expected="", devices=[], result=""):

		if (iname not in self.vLog.keys()):
			self.vLog[iname] = []

		self.vLog[iname].append({kname: {"current": current,
                                         "expected": expected,
                                         "devices": devices,
                                         "result": result}})
		return

	def get_log(self):
		return self.vLog

	def put_log(self):
		vlog = self.vLog
		self.vLog = {}
		return vlog

	def _display_device(self, log):
		ret = True
		for l in log:
			for opt, val in l.items():
				print(" %s=%s" % (opt, val["expected"]))
				for dev in val["devices"]:
					for k, v in dev.items():
						cv = v["current"]
						rs = v["result"]
						if (not rs):
							print("  %s=%s" % (k, cv))
						if (ret):
							ret = rs
		return ret

	def _display_non_device(self, log):
		ret = True
		for l in log:
			for opt, val in l.items():
				cv = val["current"]
				ev = val["expected"]
				rs = val["result"]
				print(" %s=%s"
					% (opt, cv), end="\n" if rs else ", ")
				if (not rs):
					print("[Expected: %s]" % ev)
					ret = rs
		return ret

	def _display_log(self, log):
		ret = True
		for l in log:
			for opt, val in l.items():
				if (val["current"]):
					rs = self._display_non_device([l])
				elif (not val["current"]):
					rs = self._display_device([l])
				if (ret):
					ret = rs
		return ret

	def display(self):
		ret = True
		instances = json.loads(self.put_log())
		for key in instances.keys():
			print("[%s]" % key)
			rs = self._display_log(instances[key])
			print("Verification: %s\n" % ("Pass" if rs else "Fail"))
			if ret:
				ret = rs
		return ret
