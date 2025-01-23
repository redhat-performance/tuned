from tuned.utils.class_loader import ClassLoader
from tuned.profiles.functions.parser import Parser
from tuned.profiles.functions.base import Function
import tuned.logs
import tuned.consts as consts

log = tuned.logs.get()

class Repository(ClassLoader):
	"""
	Repository of functions used within TuneD profiles.
	The functions are loaded lazily (when first used).
	"""

	def __init__(self):
		super(Repository, self).__init__()
		self._functions = {}

	@property
	def functions(self):
		return self._functions

	def _set_loader_parameters(self):
		self._namespace = "tuned.profiles.functions"
		self._prefix = consts.FUNCTION_PREFIX
		self._interface = Function

	def create(self, function_name):
		log.debug("creating function %s" % function_name)
		function_cls = self.load_class(function_name)
		function_instance = function_cls()
		self._functions[function_name] = function_instance
		return function_instance

	# load a function from its file and return it
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

	def expand(self, s):
		return Parser(self).expand(s)
