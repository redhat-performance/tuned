import unittest2
import flexmock
import tempfile
import shutil
import os

import tuned.profiles as profiles
from tuned.profiles.exceptions import InvalidProfileException

class LoaderTestCase(unittest2.TestCase):
	@classmethod
	def setUpClass(cls):
		profiles.loader.log = flexmock.flexmock(info = lambda *args: None,\
			error = lambda *args: None,debug = lambda *args: None,\
			warn = lambda *args: None)
		cls._test_dir = tempfile.mkdtemp()
		cls._profiles_dir = cls._test_dir + '/test_profiles'
		cls._dummy_profile_dir = cls._profiles_dir + '/dummy'
		cls._dummy_profile_dir2 = cls._profiles_dir + '/dummy2'
		cls._dummy_profile_dir3 = cls._profiles_dir + '/dummy3'
		cls._dummy_profile_dir4 = cls._profiles_dir + '/dummy4'
		try:
			os.mkdir(cls._profiles_dir)
			os.mkdir(cls._dummy_profile_dir)
			os.mkdir(cls._dummy_profile_dir2)
			os.mkdir(cls._dummy_profile_dir3)
			os.mkdir(cls._dummy_profile_dir4)
		except OSError:
			pass

		with open(cls._dummy_profile_dir + '/tuned.conf','w') as f:
			f.write('[main]\nsummary=dummy profile\n')
			f.write('[test_unit]\ntest_option=hello\n')
			f.write('random_option=random\n')

		with open(cls._dummy_profile_dir2 + '/tuned.conf','w') as f:
			f.write(\
			'[main]\nsummary=second dummy profile\n')
			f.write('[test_unit]\ntest_option=hello world\n')
			f.write('secondary_option=whatever\n')

		with open(cls._dummy_profile_dir3 + '/tuned.conf','w') as f:
			f.write('[main]\nsummary=another profile\ninclude=dummy\n')
			f.write('[test_unit]\ntest_option=bye bye\n')
			f.write('new_option=add this\n')

		with open(cls._dummy_profile_dir4 + '/tuned.conf','w') as f:
			f.write(\
				'[main]\nsummary=dummy profile for configuration read test\n')
			f.write('file_path=${i:PROFILE_DIR}/whatever\n')
			f.write('script=random_name.sh\n')
			f.write('[test_unit]\ntest_option=hello world\n')

	def setUp(self):
		locator = profiles.Locator([self._profiles_dir])
		factory = profiles.Factory()
		merger = profiles.Merger()
		self._loader = profiles.Loader(locator,factory,merger,None,\
			profiles.variables.Variables())

	def test_safe_name(self):
		self.assertFalse(self._loader.safe_name('*'))
		self.assertFalse(self._loader.safe_name('$'))
		self.assertTrue(self._loader.safe_name('Allowed_ch4rs.-'))

	def test_load_without_include(self):
		merged_profile = self._loader.load(['dummy','dummy2'])

		self.assertEqual(merged_profile.name, 'dummy dummy2')
		self.assertEqual(merged_profile.options['summary'],\
			'second dummy profile')
		self.assertEqual(merged_profile.units['test_unit'].\
			options['test_option'],'hello world')
		self.assertEqual(merged_profile.units['test_unit'].\
			options['secondary_option'],'whatever')

		with self.assertRaises(InvalidProfileException):
			self._loader.load([])

		with self.assertRaises(InvalidProfileException):
			self._loader.load(['invalid'])

	def test_load_with_include(self):
		merged_profile = self._loader.load(['dummy3'])

		self.assertEqual(merged_profile.name,'dummy3')
		self.assertEqual(merged_profile.options['summary'],'another profile')
		self.assertEqual(merged_profile.units['test_unit'].\
			options['test_option'],'bye bye')
		self.assertEqual(merged_profile.units['test_unit'].\
			options['new_option'],'add this')
		self.assertEqual(merged_profile.units['test_unit'].\
			options['random_option'],'random')

	def test_expand_profile_dir(self):
		self.assertEqual(self._loader._expand_profile_dir(\
			'/hello/world','${i:PROFILE_DIR}/file'),'/hello/world/file')

	def test_load_config_data(self):
		config = self._loader._load_config_data(\
			self._dummy_profile_dir4 + '/tuned.conf')

		self.assertEqual(config['main']['script'][0],\
			self._dummy_profile_dir4 + '/random_name.sh')

		self.assertEqual(config['main']['file_path'],\
			self._dummy_profile_dir4 + '/whatever')

		self.assertEqual(config['test_unit']['test_option'],\
			'hello world')

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls._test_dir)
