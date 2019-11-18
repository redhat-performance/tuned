import unittest2
import flexmock

from tuned.exports.controller import ExportsController
import tuned.exports as exports

class ControllerTestCase(unittest2.TestCase):
	@classmethod
	def setUpClass(cls):
		cls._controller = ExportsController()

	def test_is_exportable_method(self):
		self.assertFalse(self._controller._is_exportable_method( \
			MockClass().NonExportableObject))

		self.assertTrue(self._controller._is_exportable_method( \
			MockClass().ExportableMethod))

	def test_is_exportable_signal(self):
		self.assertFalse(self._controller._is_exportable_signal( \
			MockClass().NonExportableObject))

		self.assertTrue(self._controller._is_exportable_signal( \
			MockClass().ExportableSignal))

	def test_initialize_exports(self):
		local_controller = ExportsController()
		exporter = MockExporter()
		instance = MockClass()
		local_controller.register_exporter(exporter)
		local_controller.register_object(instance)
		local_controller._initialize_exports()
		self.assertEqual(exporter.exported_methods[0].method,\
			instance.ExportableMethod)
		self.assertEqual(exporter.exported_methods[0].args[0],\
			"method_param1")
		self.assertEqual(exporter.exported_methods[0].kwargs['kword'],\
			"method_param2")
		self.assertEqual(exporter.exported_signals[0].method,\
			instance.ExportableSignal)
		self.assertEqual(exporter.exported_signals[0].args[0],\
			"signal_param1")
		self.assertEqual(exporter.exported_signals[0].kwargs['kword'],\
			"signal_param2")

	def test_start_stop(self):
		local_controller = ExportsController()
		exporter = MockExporter()
		local_controller.register_exporter(exporter)
		local_controller.start()
		self.assertTrue(exporter.is_running)
		local_controller.stop()
		self.assertFalse(exporter.is_running)


class MockExporter(object):
	def __init__(self):
		self.exported_methods = []
		self.exported_signals = []
		self.is_running = False

	def export(self,method,*args,**kwargs):
		object_to_export = flexmock.flexmock(\
			method = method, args = args, kwargs = kwargs)
		self.exported_methods.append(object_to_export)

	def signal(self,method,*args,**kwargs):
		object_to_export = flexmock.flexmock(\
			method = method, args = args, kwargs = kwargs)
		self.exported_signals.append(object_to_export)

	def start(self):
		self.is_running = True

	def stop(self):
		self.is_running = False

class MockClass(object):
	@exports.export('method_param1', kword = 'method_param2')
	def ExportableMethod(self):
		return True

	def NonExportableObject(self):
		pass

	@exports.signal('signal_param1', kword = 'signal_param2')
	def ExportableSignal(self):
		return True
