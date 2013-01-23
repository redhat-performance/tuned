__all__ = ["command_set", "command_get", "command_custom"]

#	@command_set("scheduler", per_device=True)
#	def set_scheduler(self, value, device):
#		set_new_scheduler
#
#	@command_get("scheduler")
#	def get_scheduler(self, device):
#		return current_scheduler
#
#	@command_set("foo")
#	def set_foo(self, value):
#		set_new_foo
#
#	@command_get("foo")
#	def get_foo(self):
#		return current_foo
#

def command_set(name, per_device=False, priority=0):
	def wrapper(method):
		method._command = {
			"set": True,
			"name": name,
			"per_device": per_device,
			"priority": priority,
		}
		return method

	return wrapper

def command_get(name):
	def wrapper(method):
		method._command = {
			"get": True,
			"name": name,
		}
		return method
	return wrapper

def command_custom(name, per_device=False, priority=0):
	def wrapper(method):
		method._command = {
			"custom": True,
			"name": name,
			"per_device": per_device,
			"priority": priority,
		}
		return method
	return wrapper
