import unittest
import tests.globals
from flexmock import flexmock
from tuned.plugins.base import Plugin as PluginBase
import tuned.plugins.decorators

class MockPlugin(PluginBase):
	@classmethod
	def _get_default_options(cls):
		return { 'color': 'blue', 'size': 'XXL' }

class InvalidCommandPlugin(MockPlugin):
	@tuned.plugins.decorators.command_set('color')
	def _set_color(self, new_color):
		pass

class CommandPlugin(MockPlugin):
	@classmethod
	def tunable_devices(cls):
		return ['a', 'b']

	def _post_init(self):
		self._size = 'M'
		self._color = { 'a': 'green', 'b': 'pink' }

	@tuned.plugins.decorators.command_set('size')
	def _set_size(self, new_size):
		self._size = new_size

	@tuned.plugins.decorators.command_get('size')
	def _get_size(self):
		return self._size

	@tuned.plugins.decorators.command_set('color', per_device=True)
	def _set_color(self, device, new_color):
		self._color[device] = new_color

	@tuned.plugins.decorators.command_get('color')
	def _get_color(self, device):
		return self._color[device]

class PluginBaseClassTestCase(unittest.TestCase):
	def setUp(self):
		self.storage_factory = flexmock(create = lambda name: None)
		self.monitor_repository = None
		self.plugin = MockPlugin(self.monitor_repository, self.storage_factory)

	def test_init(self):
		self.storage_factory.should_receive('create').and_return(None).times(2)
		plugin = MockPlugin(self.monitor_repository, self.storage_factory, None, None)
		plugin = MockPlugin(self.monitor_repository, self.storage_factory)

	def test_cleanup(self):
		self.plugin.cleanup()

	def test_update_tuning_not_implemented(self):
		with self.assertRaises(NotImplementedError):
			self.plugin.update_tuning()

	def test_class_properties(self):
		self.assertIs(PluginBase.tunable_devices(), None)
		self.assertTrue(PluginBase.is_supported())

	def test_instance_properties(self):
		self.assertTrue(self.plugin.dynamic_tuning)

	def test_merge_unknown_options(self):
		plugin1 = PluginBase(self.monitor_repository, self.storage_factory, None, None)
		plugin2 = PluginBase(self.monitor_repository, self.storage_factory, None, {})
		plugin3 = PluginBase(self.monitor_repository, self.storage_factory, None, {'unknown': 'test'})
		self.assertDictEqual(plugin1._options, {})
		self.assertDictEqual(plugin2._options, {})
		self.assertDictEqual(plugin3._options, {})

	def test_merge_known_options(self):
		plugin1 = MockPlugin(self.monitor_repository, self.storage_factory, None, None)
		plugin2 = MockPlugin(self.monitor_repository, self.storage_factory, None, {'color': 'red'})
		plugin3 = MockPlugin(self.monitor_repository, self.storage_factory, None, {'size': 'S', 'fabric': 'cotton'})
		self.assertDictEqual(plugin1._options, {'size': 'XXL', 'color': 'blue'})
		self.assertDictEqual(plugin2._options, {'size': 'XXL', 'color': 'red'})
		self.assertDictEqual(plugin3._options, {'size': 'S', 'color': 'blue'})

	def test_classs_with_invalid_commands(self):
		with self.assertRaises(TypeError):
			plugin = InvalidCommandPlugin(self.monitor_repository, self.storage_factory)

	def test_storage_with_device_independent_commands(self):
		storage = flexmock()
		storage_factory = flexmock()
		storage_factory.should_receive('create').and_return(storage)

		storage.should_receive('set').with_args('size', 'M').once.ordered
		storage.should_receive('get').with_args('size').and_return('M').once.ordered
		storage.should_receive('unset').with_args('size').once.ordered

		plugin = CommandPlugin(self.monitor_repository, storage_factory, ['b'], {'size': 'XXS', 'color': None})
		plugin.execute_commands()
		plugin.cleanup_commands()

	def test_storage_with_per_device_commands(self):
		storage = flexmock()
		storage_factory = flexmock()
		storage_factory.should_receive('create').and_return(storage)

		storage.should_receive('set').with_args('color@b', 'pink').once.ordered
		storage.should_receive('get').with_args('color@b').and_return('pink').once.ordered
		storage.should_receive('unset').with_args('color@b').once.ordered

		plugin = CommandPlugin(self.monitor_repository, storage_factory, ['b'], {'size': None, 'color': 'white'})
		plugin.execute_commands()
		plugin.cleanup_commands()

	def test_exception_with_per_device_commands_when_no_devices_specified(self):
		storage = flexmock(set=lambda key: None, get=lambda key, value: None, unset=lambda key: None)
		storage_factory = flexmock()
		storage_factory.should_receive('create').and_return(storage)

		plugin = CommandPlugin(self.monitor_repository, storage_factory)
		with self.assertRaises(TypeError):
			plugin.execute_commands()
		with self.assertRaises(TypeError):
			plugin.cleanup_commands()
