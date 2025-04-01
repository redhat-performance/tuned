from . import base

class Exec(base.Function):
	"""
	Executes a process and returns its output.

	====
	The following executes `cat /etc/tuned/active_profile`:
	----
	${f:exec:cat:/etc/tuned/active_profile}
	----
	====
	"""
	def __init__(self):
		# unlimited number of arguments, min 1 argument (the name of executable)
		super(Exec, self).__init__("exec", 0, 1)

	def execute(self, args):
		if not super(Exec, self).execute(args):
			return None
		(ret, out) = self._cmd.execute(args)
		if ret == 0:
			return out
		return None
