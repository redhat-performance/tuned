import unittest
import tests.globals
import tuned.monitors.base

# TODO: multiple instances share the same data source (_available_devices vs _updating_devices)

class MockMonitor(tuned.monitors.base.Monitor):
	@classmethod
	def _init_available_devices(cls):
		cls._available_devices = set(["a", "b"])

	@classmethod
	def update(cls):
		for device in ["a", "b"]:
			cls._load.setdefault(device, 0)
			cls._load[device] += 1

class MonitorBaseClassTestCase(unittest.TestCase):
	def test_fail_base_class_init(self):
		with self.assertRaises(NotImplementedError):
			tuned.monitors.base.Monitor()

	def test_available_devices(self):
		monitor = MockMonitor()
		devices = MockMonitor.get_available_devices()
		self.assertEqual(devices, set(["a", "b"]))
		del monitor

	def test_registering_instances(self):
		monitor = MockMonitor()
		self.assertIn(monitor, MockMonitor.instances())

		monitor.cleanup()
		self.assertNotIn(monitor, MockMonitor.instances())
		del monitor

	def test_init_with_devices(self):
		monitor = MockMonitor()
		self.assertSetEqual(set(["a", "b"]), monitor.devices)
		del monitor

		monitor = MockMonitor(["a"])
		self.assertSetEqual(set(["a"]), monitor.devices)
		del monitor

		monitor = MockMonitor([])
		self.assertSetEqual(set(), monitor.devices)
		del monitor

		monitor = MockMonitor(["b", "x"])
		self.assertSetEqual(set(["b"]), monitor.devices)
		del monitor

	def test_add_device(self):
		monitor = MockMonitor(["a"])
		self.assertSetEqual(set(["a"]), monitor.devices)
		monitor.add_device("x")
		self.assertSetEqual(set(["a"]), monitor.devices)
		monitor.add_device("b")
		self.assertSetEqual(set(["a", "b"]), monitor.devices)
		del monitor

	def test_remove_device(self):
		monitor = MockMonitor()
		self.assertSetEqual(set(["a", "b"]), monitor.devices)
		monitor.remove_device("a")
		self.assertSetEqual(set(["b"]), monitor.devices)
		monitor.remove_device("x")
		self.assertSetEqual(set(["b"]), monitor.devices)
		monitor.remove_device("b")
		self.assertSetEqual(set(), monitor.devices)
		del monitor

	def test_get_load_from_enabled(self):
		monitor = MockMonitor()
		load = monitor.get_load()
		self.assertIn("a", load)
		self.assertIn("b", load)

		monitor.remove_device("a")
		load = monitor.get_load()
		self.assertNotIn("a", load)
		self.assertIn("b", load)

		monitor.remove_device("b")
		load = monitor.get_load()
		self.assertDictEqual({}, load)

		del monitor
