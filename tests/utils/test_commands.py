import unittest2
import tempfile
import flexmock
import shutil
import re
import os

from tuned.utils.commands import commands
import tuned.consts as consts
from tuned.exceptions import TunedException
import tuned.utils.commands

tuned.utils.commands.log = flexmock.flexmock(info = lambda *args: None,\
	error = lambda *args: None,debug = lambda *args: None,\
	warn = lambda *args: None)

class CommandsTestCase(unittest2.TestCase):
	def setUp(self):
		self._commands = commands()
		self._test_dir = tempfile.mkdtemp()
		self._test_file = tempfile.NamedTemporaryFile(mode='r',dir = self._test_dir)

	def test_get_bool(self):
		positive_values = ['y','yes','t','true']
		negative_values = ['n','no','f','false']

		for val in positive_values:
			self.assertEqual(self._commands.get_bool(val),"1")

		for val in negative_values:
			self.assertEqual(self._commands.get_bool(val),"0")

		self.assertEqual(self._commands.get_bool('bad_value'),'bad_value')

	def test_remove_ws(self):
		self.assertEqual(self._commands.remove_ws(' a  bc '),'a bc')

	def test_unquote(self):
		self.assertEqual(self._commands.unquote('"whatever"'),'whatever')

	def test_escape(self):
		self.assertEqual(self._commands.escape('\\'),'\\\\')

	def test_unescape(self):
		self.assertEqual(self._commands.unescape('\\'),'')

	def test_align_str(self):
		self.assertEqual(self._commands.align_str('abc',5,'def'),'abc  def')

	def test_dict2list(self):
		dictionary = {'key1':1,'key2':2,'key3':3}
		self.assertEqual(self._commands.dict2list(dictionary)\
			,['key1',1,'key2',2,'key3',3])

	def test_re_lookup_compile(self):
		pattern = re.compile(r'([1-9])')
		dictionary = {'[1-9]':''}
		self.assertEqual(self._commands.re_lookup_compile(dictionary).pattern\
			,pattern.pattern)
		self.assertIsNone(self._commands.re_lookup_compile(None))

	def test_multiple_re_replace(self):
		text = 'abcd1234'
		dictionary = {'abc':'gfh'}
		pattern = self._commands.re_lookup_compile(dictionary)
		self.assertEqual(self._commands.multiple_re_replace(dictionary,text)\
			,'gfhd1234')
		self.assertEqual(self._commands.multiple_re_replace(\
			dictionary,text,pattern),'gfhd1234')

	def test_re_lookup(self):
		dictionary = {'abc':'abc','mno':'mno'}
		text1 = 'abc def'
		text2 = 'jkl mno'
		text12 = 'abc mno'
		text3 = 'whatever'
		self.assertEqual(self._commands.re_lookup(dictionary,text1),'abc')
		self.assertEqual(self._commands.re_lookup(dictionary,text2),'mno')
		self.assertEqual(self._commands.re_lookup(dictionary,text12),'abc')
		self.assertIsNone(self._commands.re_lookup(dictionary,text3),None)

	def test_write_to_file(self):
		self.assertTrue(self._commands.write_to_file(self._test_file.name,\
			'hello world'))
		with open(self._test_file.name,'r') as f:
			self.assertEqual(f.read(),'hello world')

		self.assertTrue(self._commands.write_to_file(self._test_file.name,\
			'world hello'))
		with open(self._test_file.name,'r') as f:
			self.assertEqual(f.read(),'world hello')

		local_test_file = self._test_dir + '/dir' +'/self._test_file'
		self.assertTrue(self._commands.write_to_file(local_test_file,\
			'hello world',True))
		with open(local_test_file,'r') as f:
			self.assertEqual(f.read(),'hello world')

		shutil.rmtree(os.path.dirname(local_test_file))

		self.assertFalse(self._commands.write_to_file(local_test_file,\
			'hello world'))

	def test_read_file(self):
		with open(self._test_file.name,'w') as f:
			f.write('hello world')
		self.assertEqual(self._commands.read_file(self._test_file.name),\
			'hello world')
		self.assertEqual(self._commands.read_file('/bad_name','error'),\
			'error')

	def test_rmtree(self):
		test_tree = self._test_dir + '/one/two'
		os.makedirs(test_tree)
		test_tree = self._test_dir + '/one'
		self.assertTrue(self._commands.rmtree(test_tree))
		self.assertFalse(os.path.isdir(test_tree))
		self.assertTrue(self._commands.rmtree(test_tree))

	def test_unlink(self):
		local_test_file = self._test_dir + 'file_to_delete'
		open(local_test_file,'w').close()
		self.assertTrue(os.path.exists(local_test_file))
		self.assertTrue(self._commands.unlink(local_test_file))
		self.assertFalse(os.path.exists(local_test_file))
		self.assertTrue(self._commands.unlink(local_test_file))

	def test_rename(self):
		rename_test_file = self._test_dir + '/bad_name'
		open(rename_test_file,'w').close()
		self.assertTrue(self._commands.rename(rename_test_file,\
			self._test_dir + '/right_name'))
		self.assertTrue(os.path.exists(self._test_dir + '/right_name'))
		os.remove(self._test_dir + '/right_name')

	def test_copy(self):
		copy_test_file = self._test_dir + '/origo'
		with open(copy_test_file,'w') as f:
			f.write('hello world')
		self.assertTrue(self._commands.copy(copy_test_file,\
			self._test_dir + '/copy'))
		self.assertTrue(os.path.exists(self._test_dir + '/copy'))
		self.assertTrue(os.path.exists(self._test_dir + '/origo'))
		with open(self._test_dir + '/copy','r') as f:
			self.assertEqual(f.read(),'hello world')
		os.remove(self._test_dir + '/origo')
		os.remove(self._test_dir + '/copy')

	def test_replace_in_file(self):
		with open(self._test_file.name,'w') as f:
			f.write('hello world')

		self.assertTrue(self._commands.replace_in_file(self._test_file.name,\
			'hello','bye'))
		with open(self._test_file.name,'r') as f:
			self.assertEqual(f.read(),'bye world')

	def test_multiple_replace_in_file(self):
		dictionary = {'abc':'123','ghi':'456'}

		with open(self._test_file.name,'w') as f:
			f.write('abc def ghi')

		self.assertTrue(self._commands.multiple_replace_in_file(\
			self._test_file.name,dictionary))
		with open(self._test_file.name,'r') as f:
			self.assertEqual(f.read(),'123 def 456')

	def test_add_modify_option_in_file(self):
		with open(self._test_file.name,'w') as f:
			f.write('option1="123"\noption2="456"\n')

		dictionary = {'option3':789,'option1':321}
		self.assertTrue(self._commands.add_modify_option_in_file(\
			self._test_file.name,dictionary))
		with open(self._test_file.name,'r') as f:
			self.assertEqual(f.read(),\
				'option1="321"\noption2="456"\noption3="789"\n')

	def test_get_active_option(self):
		self.assertEqual(self._commands.get_active_option('opt1 [opt2] opt3'),\
			'opt2')
		self.assertEqual(self._commands.get_active_option('opt1 opt2 opt3'),\
			'opt1')
		self.assertEqual(self._commands.get_active_option(\
			'opt1 opt2 opt3',False),'opt1 opt2 opt3')

	def test_hex2cpulist(self):
		self.assertEqual(self._commands.hex2cpulist('0xf'),[0,1,2,3])
		self.assertEqual(self._commands.hex2cpulist('0x1,0000,0001'),[0,32])

	def test_cpulist_unpack(self):
		cpus = '4-8,^6,0xf00,,!10-11'
		self.assertEqual(self._commands.cpulist_unpack(cpus),[4,5,7,8,9])
		cpus = '1,2,3-x'
		self.assertEqual(self._commands.cpulist_unpack(cpus),[])
		cpus = '1,2,!3-x'
		self.assertEqual(self._commands.cpulist_unpack(cpus),[])

	def test_cpulist_pack(self):
		self.assertEqual(self._commands.cpulist_pack([0,1,3,4,5,6,8,9,32]),\
			['0-1','3-6','8-9','32'])

	def test_cpulist2hex(self):
		self.assertEqual(self._commands.cpulist2hex('1-3,5,32'),\
			'00000001,0000002e')

	def test_cpulist2bitmask(self):
		self.assertEqual(self._commands.cpulist2bitmask([1,2,3]),0b1110)
		self.assertEqual(self._commands.cpulist2bitmask([2,4,6]),0b1010100)

	def test_get_size(self):
		self.assertEqual(self._commands.get_size('100KB'),102400)
		self.assertEqual(self._commands.get_size('100Kb'),102400)
		self.assertEqual(self._commands.get_size('100kb'),102400)
		self.assertEqual(self._commands.get_size('1MB'),1024 * 1024)
		self.assertEqual(self._commands.get_size('1GB'),1024 * 1024 * 1024)

	def test_get_active_profile(self):
		consts.ACTIVE_PROFILE_FILE = self._test_dir + '/active_profile'
		consts.PROFILE_MODE_FILE = self._test_dir + '/profile_mode'
		with open(consts.ACTIVE_PROFILE_FILE,'w') as f:
			f.write('test_profile')
		with open(consts.PROFILE_MODE_FILE,'w') as f:
			f.write('auto')
		(profile,mode) = self._commands.get_active_profile()
		self.assertEqual(profile,'test_profile')
		self.assertEqual(mode,False)
		os.remove(consts.ACTIVE_PROFILE_FILE)
		os.remove(consts.PROFILE_MODE_FILE)
		(profile,mode) = self._commands.get_active_profile()
		self.assertEqual(profile,None)
		self.assertEqual(mode,None)

	def test_save_active_profile(self):
		consts.ACTIVE_PROFILE_FILE = self._test_dir + '/active_profile'
		consts.PROFILE_MODE_FILE = self._test_dir + '/profile_mode'
		self._commands.save_active_profile('test_profile',False)
		with open(consts.ACTIVE_PROFILE_FILE) as f:
			self.assertEqual(f.read(),'test_profile\n')
		with open(consts.PROFILE_MODE_FILE) as f:
			self.assertEqual(f.read(),'auto\n')
		os.remove(consts.ACTIVE_PROFILE_FILE)
		os.remove(consts.PROFILE_MODE_FILE)

	def tearDown(self):
		self._test_file.close()
		shutil.rmtree(self._test_dir)
