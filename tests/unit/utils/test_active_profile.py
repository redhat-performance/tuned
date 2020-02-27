import os
import shutil
import tempfile
import unittest2

import tuned.consts as consts
from tuned.utils.active_profile import ActiveProfileManager

class ActiveProfileManagerTestCase(unittest2.TestCase):
	def setUp(self):
		self._test_dir = tempfile.mkdtemp()

	def test_get(self):
		consts.ACTIVE_PROFILE_FILE = self._test_dir + '/active_profile'
		consts.PROFILE_MODE_FILE = self._test_dir + '/profile_mode'
		with open(consts.ACTIVE_PROFILE_FILE,'w') as f:
			f.write('test_profile')
		with open(consts.PROFILE_MODE_FILE,'w') as f:
			f.write('auto')
		active_profile_manager = ActiveProfileManager()
		(profile,mode) = active_profile_manager.get()
		self.assertEqual(profile,'test_profile')
		self.assertEqual(mode,False)
		os.remove(consts.ACTIVE_PROFILE_FILE)
		os.remove(consts.PROFILE_MODE_FILE)
		(profile,mode) = active_profile_manager.get()
		self.assertEqual(profile,None)
		self.assertEqual(mode,None)

	def test_save(self):
		consts.ACTIVE_PROFILE_FILE = self._test_dir + '/active_profile'
		consts.PROFILE_MODE_FILE = self._test_dir + '/profile_mode'
		active_profile_manager = ActiveProfileManager()
		active_profile_manager.save('test_profile', False)
		with open(consts.ACTIVE_PROFILE_FILE) as f:
			self.assertEqual(f.read(),'test_profile\n')
		with open(consts.PROFILE_MODE_FILE) as f:
			self.assertEqual(f.read(),'auto\n')
		os.remove(consts.ACTIVE_PROFILE_FILE)
		os.remove(consts.PROFILE_MODE_FILE)

	def tearDown(self):
		shutil.rmtree(self._test_dir)
