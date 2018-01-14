from . import interfaces
import inspect
import tuned.patterns

class ExportsController(tuned.patterns.Singleton):
	"""
	Controls and manages object interface exporting.
	"""

	def __init__(self):
		super(ExportsController, self).__init__()
		self._exporters = []
		self._objects = []
		self._exports_initialized = False

	def register_exporter(self, instance):
		"""Register objects exporter."""
		self._exporters.append(instance)

	def register_object(self, instance):
		"""Register object to be exported."""
		self._objects.append(instance)

	def _is_exportable_method(self, method):
		"""Check if method was marked with @exports.export wrapper."""
		return inspect.ismethod(method) and hasattr(method, "export_params")

	def _is_exportable_signal(self, method):
		"""Check if method was marked with @exports.signal wrapper."""
		return inspect.ismethod(method) and hasattr(method, "signal_params")

	def _export_method(self, method):
		"""Register method to all exporters."""
		for exporter in self._exporters:
			args = method.export_params[0]
			kwargs = method.export_params[1]
			exporter.export(method, *args, **kwargs)

	def _export_signal(self, method):
		"""Register signal to all exporters."""
		for exporter in self._exporters:
			args = method.signal_params[0]
			kwargs = method.signal_params[1]
			exporter.signal(method, *args, **kwargs)

	def _initialize_exports(self):
		if self._exports_initialized:
			return

		for instance in self._objects:
			for name, method in inspect.getmembers(instance, self._is_exportable_method):
				self._export_method(method)
			for name, method in inspect.getmembers(instance, self._is_exportable_signal):
				self._export_signal(method)

		self._exports_initialized = True

	def start(self):
		"""Start the exports."""
		self._initialize_exports()
		for exporter in self._exporters:
			exporter.start()

	def stop(self):
		"""Stop the exports."""
		for exporter in self._exporters:
			exporter.stop()
