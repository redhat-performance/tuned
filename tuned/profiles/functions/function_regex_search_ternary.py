import re
from . import base

class regex_search_ternary(base.Function):
	"""
	Ternary regex operator, it takes arguments in the following form
	STR1, REGEX, STR2, STR3
	If REGEX matches STR1 (re.search is used), STR2 is returned,
	otherwise STR3 is returned
	"""
	def __init__(self):
		# 4 arguments
		super(regex_search_ternary, self).__init__("regex_search_ternary", 4, 4)

	def execute(self, args):
		if not super(regex_search_ternary, self).execute(args):
			return None
		if re.search(args[1], args[0]):
			return args[2]
		else:
			return args[3]
