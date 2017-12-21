import unittest
import tempfile
import shutil
import os.path
import tuned.profiles.exceptions
from tuned.profiles.loader import Loader
from flexmock import flexmock

class MockProfile(object):
	def __init__(self, name, config):
		self.name = name
		self.options = {}
		self.units = {}
		self.test_config = config

class MockProfileFactory(object):
	def create(self, name, config):
		return MockProfile(name, config)

class MockProfileMerger(object):
	def merge(self, profiles):
		new = MockProfile("merged", {})
		new.test_merged = profiles
		return new

class LoaderTestCase(unittest.TestCase):
	def setUp(self):
		self.factory = MockProfileFactory()
		self.merger = MockProfileMerger()
		self.loader = Loader(self._tmp_load_dirs, self.factory, self.merger)

	@classmethod
	def setUpClass(cls):
		tmpdir1 = tempfile.mkdtemp()
		tmpdir2 = tempfile.mkdtemp()
		cls._tmp_load_dirs = [tmpdir1, tmpdir2]

		cls._create_profile(tmpdir1, "default", "[main]\n\n[network]\ntype=net\ndevices=em*\n\n[disk]\nenabled=false\n")
		cls._create_profile(tmpdir1, "invalid", "INVALID")
		cls._create_profile(tmpdir1, "expand", "[expand]\ntype=script\nscript=runme.sh\n")
		cls._create_profile(tmpdir2, "empty", "")

		cls._create_profile(tmpdir1, "custom", "[custom]\ntype=one\n")
		cls._create_profile(tmpdir2, "custom", "[custom]\ntype=two\n")

	@classmethod
	def tearDownClass(cls):
		for tmp_dir in cls._tmp_load_dirs:
			shutil.rmtree(tmp_dir, True)

	@classmethod
	def _create_profile(cls, load_dir, profile_name, tuned_conf_content):
		profile_dir = os.path.join(load_dir, profile_name)
		conf_name = os.path.join(profile_dir, "tuned.conf")
		os.mkdir(profile_dir)
		with open(conf_name, "w") as conf_file:
			conf_file.write(tuned_conf_content)

	def test_init(self):
		Loader([], None, None)
		Loader(["/tmp"], None, None)
		Loader(["/foo", "/bar"], None, None)

	def test_init_wrong_type(self):
		with self.assertRaises(TypeError):
			Loader(False, self.factory, self.merger)

	def test_load(self):
		profile = self.loader.load("default")
		self.assertIn("main", profile.test_config)
		self.assertIn("disk", profile.test_config)
		self.assertEqual(profile.test_config["network"]["devices"], "em*")

	def test_load_empty(self):
		profile = self.loader.load("empty")
		self.assertDictEqual(profile.test_config, {})

	def test_load_invalid(self):
		with self.assertRaises(tuned.profiles.exceptions.InvalidProfileException):
			invalid_config = self.loader.load("invalid")

	def test_load_nonexistent(self):
		with self.assertRaises(tuned.profiles.exceptions.InvalidProfileException):
			config = self.loader.load("nonexistent")

	def test_load_order(self):
		profile = self.loader.load("custom")
		self.assertEqual(profile.test_config["custom"]["type"], "two")

	def test_default_load(self):
		profile = self.loader.load("empty")
		self.assertIs(type(profile), MockProfile)

	def test_script_expand_names(self):
		profile = self.loader.load("expand")
		expected_name = os.path.join(self._tmp_load_dirs[0], "expand", "runme.sh")
		self.assertEqual(profile.test_config["expand"]["script"], expected_name)

	def test_load_multiple_profiles(self):
		profile = self.loader.load(["default", "expand"])
		self.assertEqual(len(profile.test_merged), 2)

	def test_include_directive(self):
		profile1 = MockProfile("first", {})
		profile1.options = {"include": "default"}
		profile2 = MockProfile("second", {})

		flexmock(self.factory).should_receive("create").and_return(profile1).and_return(profile2).twice()
		profile = self.loader.load("empty")

		self.assertEqual(len(profile.test_merged), 2)
