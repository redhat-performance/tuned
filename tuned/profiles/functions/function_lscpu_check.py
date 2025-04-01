import re
from . import base

class LSCPUCheck(base.Function):
	"""
	Checks regexes against the output of `lscpu`.

	Accepts arguments in the form `REGEX1, STR1, REGEX2, STR2, ...[, STR_FALLBACK]`.

	If `REGEX1` has a match in the output of `lscpu`, it returns `STR1`.
	
	If `REGEX2` has a match, it returns `STR2`.

	The function stops on the first match, i.e., if `REGEX1` has a match,
	no more regexes are processed. If no regex has a match, `STR_FALLBACK`
	is returned. If there is no fallback value, returns an empty string.
	"""
	def __init__(self):
		# unlimited number of arguments, min 2 arguments
		super(LSCPUCheck, self).__init__("lscpu_check", 0, 2)

	def execute(self, args):
		if not super(LSCPUCheck, self).execute(args):
			return None
		# Stdout is the 2nd result from the execute call
		_, lscpu = self._cmd.execute("lscpu")
		for i in range(0, len(args), 2):
			if i + 1 < len(args):
				if re.search(args[i], lscpu, re.MULTILINE):
					return args[i + 1]
		if len(args) % 2:
			return args[-1]
		else:
			return ""
