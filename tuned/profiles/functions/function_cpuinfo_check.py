import re
import tuned.logs
from . import base

log = tuned.logs.get()

class CPUInfoCheck(base.Function):
	"""
	Checks regexes against the content of `/proc/cpuinfo`.

	Accepts arguments in the form `REGEX1, STR1, REGEX2, STR2, ...[, STR_FALLBACK]`.

	If `REGEX1` has a match in `/proc/cpuinfo`, it returns `STR1`.

	If `REGEX2` has a match, it returns `STR2`.

	The function stops on the first match, i.e., if `REGEX1` has a match,
	no more regexes are processed. If no regex has a match, `STR_FALLBACK`
	is returned. If there is no fallback value, it returns an empty string.
	"""
	def __init__(self):
		# unlimited number of arguments, min 2 arguments
		super(CPUInfoCheck, self).__init__("cpuinfo_check", 0, 2)

	def execute(self, args):
		if not super(CPUInfoCheck, self).execute(args):
			return None
		cpuinfo = self._cmd.read_file("/proc/cpuinfo")
		for i in range(0, len(args), 2):
			if i + 1 < len(args):
				if re.search(args[i], cpuinfo, re.MULTILINE):
					return args[i + 1]
		if len(args) % 2:
			return args[-1]
		else:
			return ""
