import unittest
import tempfile
import shutil
import os

import tuned.consts as consts
import tuned.utils.global_config as global_config

class GlobalConfigTestCase(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.test_dir = tempfile.mkdtemp()
		with open(cls.test_dir + '/test_config','w') as f:
			f.write('test_option = hello #this is comment\ntest_bool = 1\ntest_size = 12MB\n'\
				+ '/sys/bus/pci/devices/0000:00:02.0/power/control=auto\n'\
				+ '/sys/bus/pci/devices/0000:04:00.0/power/control=auto\n'\
				+ 'false_bool=0\n'\
				+ consts.CFG_LOG_FILE_COUNT + " = " + str(consts.CFG_DEF_LOG_FILE_COUNT) + "1\n")

		cls._global_config = global_config.GlobalConfig(\
			cls.test_dir + '/test_config')

	def test_get(self):
		self.assertEqual(self._global_config.get('test_option'), 'hello')
		self.assertEqual(self._global_config.get('/sys/bus/pci/devices/0000:00:02.0/power/control'), 'auto')

	def test_get_bool(self):
		self.assertTrue(self._global_config.get_bool('test_bool'))
		self.assertFalse(self._global_config.get_bool('false_bool'))

	def test_get_size(self):
		self.assertEqual(self._global_config.get_size('test_size'),\
			12*1024*1024)

		self._global_config.set('test_size', 'bad_value')

		self.assertIsNone(self._global_config.get_size('test_size'))

	def test_default(self):
		daemon = self._global_config.get(consts.CFG_DAEMON)
		self.assertEqual(daemon, consts.CFG_DEF_DAEMON)

		log_file_count = self._global_config.get(consts.CFG_LOG_FILE_COUNT)
		self.assertIsNotNone(log_file_count)
		self.assertNotEqual(log_file_count, consts.CFG_DEF_LOG_FILE_COUNT)

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls.test_dir)
