import tuned.monitors

class LoadMonitor(tuned.monitors.Monitor):
	@classmethod
	def _init_available_devices(cls):
		cls._available_devices = set(["system"])

	@classmethod
	def update(cls):
		with open("/proc/loadavg") as statfile:
			data = statfile.read().split()
		cls._load["system"] = float(data[0])
