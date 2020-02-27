from .library import CPUInfoLibrary
import tuned.logs
from tuned.profiles.functions import base
from tuned.utils.file import FileHandler

log = tuned.logs.get()

class cpuinfo_check(base.Function):
	"""
	Checks regexes against /proc/cpuinfo. Accepts arguments in the
	following form: REGEX1, STR1, REGEX2, STR2, ...[, STR_FALLBACK]
	If REGEX1 matches something in /proc/cpuinfo it expands to STR1,
	if REGEX2 matches it expands to STR2. It stops on the first match,
	i.e. if REGEX1 matches, no more regexes are processed. If none
	regex matches it expands to STR_FALLBACK. If there is no fallback,
	it expands to empty string.
	"""
	def __init__(self):
		# unlimited number of arguments, min 2 arguments
		super(cpuinfo_check, self).__init__("cpuinfo_check", 0, 2)
		file_handler = FileHandler(log_func=log.debug)
		self._lib = CPUInfoLibrary(file_handler)

	def execute(self, args):
		if not super(cpuinfo_check, self).execute(args):
			return None
		return self._lib.cpuinfo_match(args)
