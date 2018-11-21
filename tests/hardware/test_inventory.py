import unittest2
from flexmock import flexmock
import pyudev

from tuned.hardware.inventory import Inventory

subsystem_name = "test subsystem"

class InventoryTestCase(unittest2.TestCase):
	@classmethod
	def setUpClass(cls):
		cls._context = pyudev.Context()
		cls._inventory = Inventory(set_receive_buffer_size=False)
		cls._dummy = DummyPlugin()
		cls._dummier = DummyPlugin()

	def test_get_device(self):
		try:
			device1 = pyudev.Devices.from_name(self._context, "tty", "tty0")
		except AttributeError:
			device1 = pyudev.Device.from_name(self._context, "tty", "tty0")
		device2 = self._inventory.get_device("tty", "tty0")
		self.assertEqual(device1,device2)

	def test_get_devices(self):
		device_list1 = self._context.list_devices(subsystem = "tty")
		device_list2 = self._inventory.get_devices("tty")
		self.assertItemsEqual(device_list1,device_list2)

	def test_subscribe(self):
		self._inventory.subscribe(self._dummy,subsystem_name,
				self._dummy.TestCallback)
		self._inventory.subscribe(self._dummier,subsystem_name,
				self._dummier.TestCallback)
		device = flexmock(subsystem = subsystem_name)
		self._inventory._handle_udev_event("test event", device)
		self.assertTrue(self._dummy.CallbackWasCalled)
		self.assertTrue(self._dummier.CallbackWasCalled)

	def test_unsubscribe(self):
		self._dummy.CallbackWasCalled = False
		self._dummier.CallbackWasCalled = False
		self._inventory.unsubscribe(self._dummy)
		device = flexmock(subsystem = subsystem_name)
		self._inventory._handle_udev_event("test event", device)
		self.assertFalse(self._dummy.CallbackWasCalled)
		self.assertTrue(self._dummier.CallbackWasCalled)
		self._dummier.CallbackWasCalled = False
		self._inventory.unsubscribe(self._dummier)
		self._inventory._handle_udev_event("test event", device)
		self.assertFalse(self._dummy.CallbackWasCalled)
		self.assertFalse(self._dummier.CallbackWasCalled)
		self.assertIsNone(self._inventory._monitor_observer)

class DummyPlugin():
	def __init__(self):
		self.CallbackWasCalled = False

	def TestCallback(self, event, device):
		self.CallbackWasCalled = True
