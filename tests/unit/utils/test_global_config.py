import unittest2
import flexmock
import tempfile
import shutil
import os

import tuned.consts as consts
import tuned.utils.global_config as global_config

class GlobalConfigTestCase(unittest2.TestCase):
	@classmethod
	def setUpClass(cls):
		global_config.log = flexmock.flexmock(info = lambda *args: None,\
			error = lambda *args: None,debug = lambda *args: None,\
			warn = lambda *args: None)

		cls.test_dir = tempfile.mkdtemp()
		with open(cls.test_dir + '/test_config','w') as f:
			f.write('test_option = hello\ntest_bool = 1\ntest_size = 12MB\n'\
				+ 'false_bool=0\n')

		cls._global_config = global_config.GlobalConfig(\
			cls.test_dir + '/test_config')

	def test_get(self):
		self.assertEqual(self._global_config.get('test_option'), 'hello')

	def test_get_bool(self):
		self.assertTrue(self._global_config.get_bool('test_bool'))
		self.assertFalse(self._global_config.get_bool('false_bool'))

	def test_get_size(self):
		self.assertEqual(self._global_config.get_size('test_size'),\
			12*1024*1024)

		self._global_config.set('test_size','bad_value')

		self.assertIsNone(self._global_config.get_size('test_size'))

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls.test_dir)
