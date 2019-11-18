try:
	from collections.abc import Mapping
except ImportError:
	from collections import Mapping
import tempfile
import unittest2
import flexmock

from tuned.monitors.repository import Repository
import tuned.plugins.decorators as decorators
from tuned.plugins.base import Plugin
import tuned.hardware as hardware
import tuned.monitors as monitors
import tuned.profiles as profiles
import tuned.plugins as plugins
import tuned.consts as consts
from tuned import storage
import tuned.plugins.base

tuned.plugins.base.log = flexmock.flexmock(info = lambda *args: None,\
	error = lambda *args: None,debug = lambda *args: None,\
	warn = lambda *args: None)

temp_storage_file = tempfile.TemporaryFile(mode = 'r')
consts.DEFAULT_STORAGE_FILE = temp_storage_file.name
monitors_repository = monitors.Repository()
hardware_inventory = hardware.Inventory(set_receive_buffer_size=False)
device_matcher = hardware.DeviceMatcher()
device_matcher_udev = hardware.DeviceMatcherUdev()
plugin_instance_factory = plugins.instance.Factory()
storage_provider = storage.PickleProvider()
storage_factory = storage.Factory(storage_provider)

class PluginBaseTestCase(unittest2.TestCase):
	def setUp(self):
		self._plugin = DummyPlugin(monitors_repository,storage_factory,\
			hardware_inventory,device_matcher,device_matcher_udev,\
			plugin_instance_factory,None,None)

		self._commands_plugin = CommandsPlugin(monitors_repository,\
			storage_factory,hardware_inventory,device_matcher,\
			device_matcher_udev,plugin_instance_factory,None,\
			profiles.variables.Variables())

	def test_get_effective_options(self):
		self.assertEqual(self._plugin._get_effective_options(\
			{'default_option1':'default_value2'}),\
			{'default_option1': 'default_value2',\
			'default_option2': 'default_value2'})

	def test_option_bool(self):
		self.assertTrue(self._plugin._option_bool(True))
		self.assertTrue(self._plugin._option_bool('true'))
		self.assertFalse(self._plugin._option_bool('false'))

	def test_create_instance(self):
		instance = self._plugin.create_instance(\
			'first_instance','test','test','test','test',\
			{'default_option1':'default_value2'})
		self.assertIsNotNone(instance)

	def test_destroy_instance(self):
		instance = self._plugin.create_instance(\
			'first_instance','test','test','test','test',\
			{'default_option1':'default_value2'})
		instance.plugin.init_devices()

		self._plugin.destroy_instance(instance)
		self.assertIn(instance,self._plugin.cleaned_instances)

	def test_get_matching_devices(self):
		""" without udev regex """
		instance = self._plugin.create_instance(\
			'first_instance','right_device*',None,'test','test',\
			{'default_option1':'default_value2'})

		self.assertEqual(self._plugin._get_matching_devices(\
			instance,['bad_device','right_device1','right_device2']),\
			set(['right_device1','right_device2']))

		""" with udev regex """
		instance = self._plugin.create_instance(\
			'second_instance','right_device*','device[1-2]','test','test',\
			{'default_option1':'default_value2'})

		device1 = DummyDevice('device1',{'name':'device1'})
		device2 = DummyDevice('device2',{'name':'device2'})
		device3 = DummyDevice('device3',{'name':'device3'})

		self.assertEqual(self._plugin._get_matching_devices(\
			instance,[device1,device2,device3]),set(['device1','device2']))

	def test_autoregister_commands(self):
		self._commands_plugin._autoregister_commands()
		self.assertEqual(self._commands_plugin._commands['size']['set'],\
			self._commands_plugin._set_size)
		self.assertEqual(self._commands_plugin._commands['size']['get'],\
			self._commands_plugin._get_size)
		self.assertEqual(\
			self._commands_plugin._commands['custom_name']['custom'],
			self._commands_plugin.the_most_custom_command)

	def test_check_commands(self):
		self._commands_plugin._check_commands()

		with self.assertRaises(TypeError):
			bad_plugin = BadCommandsPlugin(monitors_repository,storage_factory,\
				hardware_inventory,device_matcher,device_matcher_udev,\
				plugin_instance_factory,None,None)

	def test_execute_all_non_device_commands(self):
		instance = self._commands_plugin.create_instance('test_instance','',\
			'','','',{'size':'XXL'})

		self._commands_plugin._execute_all_non_device_commands(instance)

		self.assertEqual(self._commands_plugin._size,'XXL')

	def test_execute_all_device_commands(self):
		instance = self._commands_plugin.create_instance('test_instance','',\
			'','','',{'device_setting':'010'})

		device1 = DummyDevice('device1',{})
		device2 = DummyDevice('device2',{})

		self._commands_plugin._execute_all_device_commands(instance,\
			[device1,device2])

		self.assertEqual(device1.setting,'010')
		self.assertEqual(device2.setting,'010')

	def test_process_assignment_modifiers(self):
		self.assertEqual(self._plugin._process_assignment_modifiers('100',None)\
			,'100')
		self.assertEqual(self._plugin._process_assignment_modifiers(\
			'>100','200'),None)
		self.assertEqual(self._plugin._process_assignment_modifiers(\
			'<100','200'),'100')

	def test_get_current_value(self):
		instance = self._commands_plugin.create_instance('test_instance','',\
			'','','',{})

		command = [com for com in self._commands_plugin._commands.values()\
			if com['name'] == 'size'][0]

		self.assertEqual(self._commands_plugin._get_current_value(command),'S')

	def test_norm_value(self):
		self.assertEqual(self._plugin._norm_value('"000000021"'),'21')

	def test_verify_value(self):
		self.assertEqual(self._plugin._verify_value(\
			'test_value','1',None,True),True)

		self.assertEqual(self._plugin._verify_value(\
			'test_value','1',None,False),False)

		self.assertEqual(self._plugin._verify_value(\
			'test_value','00001','001',False),True)

		self.assertEqual(self._plugin._verify_value(\
			'test_value','0x1a','0x1a',False),True)

		self.assertEqual(self._plugin._verify_value(\
			'test_value','0x1a','0x1b',False),False)

	@classmethod
	def tearDownClass(cls):
		temp_storage_file.close()

class DummyPlugin(Plugin):
	def __init__(self,*args,**kwargs):
		super(DummyPlugin,self).__init__(*args,**kwargs)
		self.cleaned_instances = []

	@classmethod
	def _get_config_options(self):
		return {'default_option1':'default_value1',\
			'default_option2':'default_value2'}

	def _instance_cleanup(self, instance):
		self.cleaned_instances.append(instance)

	def _get_device_objects(self, devices):
		objects = []
		for device in devices:
			objects.append({'name':device})
		return devices

class DummyDevice(Mapping):
	def __init__(self,sysname,dictionary,*args,**kwargs):
		super(DummyDevice,self).__init__(*args,**kwargs)
		self.dictionary = dictionary
		self.properties = dictionary
		self.sys_name = sysname
		self.setting = '101'

	def __getitem__(self,prop):
		return self.dictionary.__getitem__(prop)

	def __len__(self):
		return self.dictionary.__len__()

	def __iter__(self):
		return self.dictionary.__iter__()

class CommandsPlugin(Plugin):
	def __init__(self,*args,**kwargs):
		super(CommandsPlugin,self).__init__(*args,**kwargs)
		self._size = 'S'

	@classmethod
	def _get_config_options(self):
		"""Default configuration options for the plugin."""
		return {'size':'S','device_setting':'101'}

	@decorators.command_set('size')
	def _set_size(self, new_size, sim):
		self._size = new_size
		return new_size

	@decorators.command_get('size')
	def _get_size(self):
		return self._size

	@decorators.command_set('device_setting',per_device = True)
	def _set_device_setting(self,value,device,sim):
		device.setting = value
		return device.setting

	@decorators.command_get('device_setting')
	def _get_device_setting(self,device,ignore_missing = False):
		return device.setting

	@decorators.command_custom('custom_name')
	def the_most_custom_command(self):
		return True

class BadCommandsPlugin(Plugin):
	def __init__(self,*args,**kwargs):
		super(BadCommandsPlugin,self).__init__(*args,**kwargs)
		self._size = 'S'

	@decorators.command_set('size')
	def _set_size(self, new_size):
		self._size = new_size
