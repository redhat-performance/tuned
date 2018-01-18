from tuned.utils.plugin_loader import PluginLoader
from . import base
import tuned.logs
import tuned.consts as consts
from tuned.utils.commands import commands

log = tuned.logs.get()

class Repository(PluginLoader):

	def __init__(self):
		super(Repository, self).__init__()
		self._functions = {}

	@property
	def functions(self):
		return self._functions

	def _set_loader_parameters(self):
		self._namespace = "tuned.profiles.functions"
		self._prefix = consts.FUNCTION_PREFIX
		self._interface = tuned.profiles.functions.base.Function

	def create(self, function_name):
		log.debug("creating function %s" % function_name)
		function_cls = self.load_plugin(function_name)
		function_instance = function_cls()
		self._functions[function_name] = function_instance
		return function_instance

	# loads function from plugin file and return it
	# if it is already loaded, just return it, it is not loaded again
	def load_func(self, function_name):
		if not function_name in self._functions:
			return self.create(function_name)
		return self._functions[function_name]

	def delete(self, function):
		assert isinstance(function, self._interface)
		log.debug("removing function %s" % function)
		for k, v in list(self._functions.items()):
			if v == function:
				del self._functions[k]
