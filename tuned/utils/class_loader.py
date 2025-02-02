import tuned.logs
import os

__all__ = ["ClassLoader"]

log = tuned.logs.get()

class ClassLoader(object):
	__slots__ = ["_namespace", "_prefix", "_interface"]

	def _set_loader_parameters(self):
		"""
		This method has to be implemented in child class and should
		set _namespace, _prefix, and _interface member attributes.
		"""
		raise NotImplementedError()

	def __init__(self):
		super(ClassLoader, self).__init__()

		self._namespace = None
		self._prefix = None
		self._interface = None
		self._set_loader_parameters()
		assert type(self._namespace) is str
		assert type(self._prefix) is str
		assert type(self._interface) is type and issubclass(self._interface, object)

	def load_class(self, class_name):
		assert type(class_name) is str
		module_name = "%s.%s%s" % (self._namespace, self._prefix, class_name)
		return self._get_class(module_name)

	def _get_class(self, module_name):
		log.debug("loading module %s" % module_name)
		module = __import__(module_name)
		path = module_name.split(".")
		path.pop(0)

		while len(path) > 0:
			module = getattr(module, path.pop(0))

		for name in module.__dict__:
			cls = getattr(module, name)
			if type(cls) is type and issubclass(cls, self._interface):
				return cls

		raise ImportError("Cannot find the class %s." % module_name)

	def load_all_classes(self):
		package = __import__(self._namespace)
		basename = self._namespace.split(".")[-1]
		classes = []
		for module_name in os.listdir(getattr(package, basename).__path__[0]):
			try:
				module_name = os.path.splitext(module_name)[0]
				if not module_name.startswith(self._prefix):
					continue
				next_class = self._get_class(
					"%s.%s" % (self._namespace, module_name)
					)
				if next_class not in classes:
					classes.append(next_class)
			except ImportError:
				pass
		return classes

