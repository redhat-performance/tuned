class CPULatencyLibrary(object):
	def __init__(self, file_handler, logger):
		self._file_handler = file_handler
		self._log = logger

	def get_intel_pstate_attr(self, attr):
		path = "/sys/devices/system/cpu/intel_pstate/%s" % attr
		try:
			contents = self._file_handler.read(path)
			return contents.strip()
		except IOError as e:
			self._log.error("Failed to get intel_pstate attribute '%s': %s"
					% (attr, e))
			return None

	def set_intel_pstate_attr(self, attr, val):
		if val is None:
			return
		try:
			path = "/sys/devices/system/cpu/intel_pstate/%s" % attr
			self._file_handler.write(path, val)
		except IOError as e:
			self._log.error("Failed to set intel_pstate attribute '%s' to '%s': %s"
					% (attr, val, e))

	def get_available_governors(self, device):
		path = "/sys/devices/system/cpu/%s/cpufreq/scaling_available_governors" % device
		try:
			contents = self._file_handler.read(path)
			return contents.strip().split()
		except IOError as e:
			self._log.error("Failed to read scaling governors available on cpu '%s': %s"
					% (device, e))
			return []

	def get_governor_on_cpu(self, cpu, no_error):
		path = "/sys/devices/system/cpu/%s/cpufreq/scaling_governor" % cpu
		try:
			contents = self._file_handler.read(path)
			return contents.strip()
		except IOError as e:
			if not no_error:
				self._log.error("Failed to read scaling governor on cpu '%s': %s"
						% (cpu, e))
			return ""

	def set_governor_on_cpu(self, governor, cpu):
		self._log.info("setting governor '%s' on cpu '%s'"
				% (governor, cpu))
		try:
			path = "/sys/devices/system/cpu/%s/cpufreq/scaling_governor" % cpu
			self._file_handler.write(path, governor)
		except IOError as e:
			self._log.error("Failed to set scaling governor to '%s' on cpu '%s': %s"
					% (governor, cpu, e))

	@staticmethod
	def sampling_down_factor_path(governor = "ondemand"):
		return "/sys/devices/system/cpu/cpufreq/%s/sampling_down_factor" % governor

	def get_sampling_down_factor(self, path, governor):
		try:
			contents = self._file_handler.read(path)
			return contents.strip()
		except IOError as e:
			self._log.error("Failed to get sampling_down_factor for governor '%s': %s"
					% (governor, e))
			return ""

	def set_sampling_down_factor(self, path, value, governor):
		self._log.info("setting sampling_down_factor to '%s' for governor '%s'"
				% (value, governor))
		try:
			self._file_handler.write(path, value)
		except IOError as e:
			self._log.error("Failed to set sampling_down_factor to '%s' for governor '%s': %s"
					% (value, governor, e))
