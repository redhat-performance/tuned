import unittest
import tests.globals
import tuned.monitors.base

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

	def test_update_fail_with_base_class(self):
		with self.assertRaises(NotImplementedError):
			tuned.monitors.base.Monitor.update()

	def test_available_devices(self):
		monitor = MockMonitor()
		devices = MockMonitor.get_available_devices()
		self.assertEqual(devices, set(["a", "b"]))
		monitor.cleanup()

	def test_registering_instances(self):
		monitor = MockMonitor()
		self.assertIn(monitor, MockMonitor.instances())
		monitor.cleanup()
		self.assertNotIn(monitor, MockMonitor.instances())

	def test_init_with_devices(self):
		monitor = MockMonitor()
		self.assertSetEqual(set(["a", "b"]), monitor.devices)
		monitor.cleanup()

		monitor = MockMonitor(["a"])
		self.assertSetEqual(set(["a"]), monitor.devices)
		monitor.cleanup()

		monitor = MockMonitor([])
		self.assertSetEqual(set(), monitor.devices)
		monitor.cleanup()

		monitor = MockMonitor(["b", "x"])
		self.assertSetEqual(set(["b"]), monitor.devices)
		monitor.cleanup()

	def test_add_device(self):
		monitor = MockMonitor(["a"])
		self.assertSetEqual(set(["a"]), monitor.devices)
		monitor.add_device("x")
		self.assertSetEqual(set(["a"]), monitor.devices)
		monitor.add_device("b")
		self.assertSetEqual(set(["a", "b"]), monitor.devices)
		monitor.cleanup()

	def test_remove_device(self):
		monitor = MockMonitor()
		self.assertSetEqual(set(["a", "b"]), monitor.devices)
		monitor.remove_device("a")
		self.assertSetEqual(set(["b"]), monitor.devices)
		monitor.remove_device("x")
		self.assertSetEqual(set(["b"]), monitor.devices)
		monitor.remove_device("b")
		self.assertSetEqual(set(), monitor.devices)
		monitor.cleanup()

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

		monitor.cleanup()

	def test_refresh_of_updating_devices(self):
		monitor1 = MockMonitor(["a"])
		self.assertSetEqual(set(["a"]), MockMonitor._updating_devices)
		monitor2 = MockMonitor(["a", "b"])
		self.assertSetEqual(set(["a", "b"]), MockMonitor._updating_devices)
		monitor1.cleanup()
		self.assertSetEqual(set(["a", "b"]), MockMonitor._updating_devices)
		monitor2.cleanup()
		self.assertSetEqual(set(), MockMonitor._updating_devices)
