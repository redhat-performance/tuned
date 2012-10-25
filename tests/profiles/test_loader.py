import unittest
import tempfile
import shutil
import os.path
import tuned.profiles.loader

# DI: return config itself instead of the profile
class MockLoader(tuned.profiles.loader.Loader):
	def _create_profile(self, profile_name, config):
		return config

class MockMerger(object):
	def merge(self, configs):
		return configs

class LoaderTestCase(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		tmpdir1 = tempfile.mkdtemp()
		tmpdir2 = tempfile.mkdtemp()
		cls._tmp_load_dirs = [tmpdir1, tmpdir2]

		cls._create_profile(tmpdir1, "default", "[main]\n\n[network]\ntype=net\ndevices=em*\n\n[disk]\nenabled=false\n")
		cls._create_profile(tmpdir1, "invalid", "INVALID")
		cls._create_profile(tmpdir1, "expand", "[expand]\ntype=script\nscript=runme.sh\n")
		cls._create_profile(tmpdir2, "empty", "")
		cls._create_profile(tmpdir2, "hasinclude", "[main]\ninclude=default\n\n[other]\nenabled=true")

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
		tuned.profiles.loader.Loader([], None)
		tuned.profiles.loader.Loader(["/tmp"], None)
		tuned.profiles.loader.Loader(["/foo", "/bar"], None)

	def test_init_wrong_type(self):
		with self.assertRaises(TypeError):
			tuned.profiles.loader.Loader(False)

	def test_add_directory(self):
		loader = tuned.profiles.loader.Loader([], None)
		self.assertEqual(len(loader.load_directories), 0);

		loader.add_directory("/a")
		self.assertEqual(len(loader.load_directories), 1);

		loader.add_directory("/b")
		self.assertEqual(len(loader.load_directories), 2);

		self.assertEqual(loader.load_directories[0], "/a")
		self.assertEqual(loader.load_directories[1], "/b")

	def test_load(self):
		loader = MockLoader(self._tmp_load_dirs, None)
		default_config = loader.load("default")

		self.assertIn("main", default_config)
		self.assertIn("network", default_config)
		self.assertIn("disk", default_config)

		self.assertEquals(default_config["network"]["devices"], "em*")
		self.assertEquals(default_config["disk"]["enabled"], "false") # TODO: improve parser

	def test_unit_set_correct_type(self):
		loader = MockLoader(self._tmp_load_dirs, None)
		config = loader.load("default")
		self.assertEqual("net", config["network"]["type"])
		self.assertEqual("disk", config["disk"]["type"])

	def test_load_empty(self):
		loader = MockLoader(self._tmp_load_dirs, None)
		empty_config = loader.load("empty")
		self.assertEquals(empty_config, {})

	def test_load_invalid(self):
		loader = MockLoader(self._tmp_load_dirs, None)
		with self.assertRaises(tuned.profiles.exceptions.InvalidProfileException):
			invalid_config = loader.load("invalid")

	def test_load_nonexistent(self):
		loader = MockLoader(self._tmp_load_dirs, None)
		with self.assertRaises(tuned.profiles.exceptions.InvalidProfileException):
			config = loader.load("nonexistent")

	def test_load_order(self):
		loader = MockLoader(self._tmp_load_dirs, None)
		custom_config = loader.load("custom")
		self.assertEquals(custom_config["custom"]["type"], "two")

	def test_default_load(self):
		loader = tuned.profiles.loader.Loader(self._tmp_load_dirs, None)
		config = loader.load("empty")
		self.assertIs(type(config), tuned.profiles.profile.Profile)

	def test_default_unit_options(self):
		loader = MockLoader(self._tmp_load_dirs, None)
		config = loader.load("default")
		self.assertIn("network", config)
		self.assertIn("enabled", config["network"])
		self.assertIn("replace", config["network"])
		self.assertIn("devices", config["network"])
		self.assertIn("type", config["network"])

	def test_script_expand_names(self):
		loader = MockLoader(self._tmp_load_dirs, None)
		config = loader.load("expand")
		expected_name = os.path.join(self._tmp_load_dirs[0], "expand", "runme.sh")
		self.assertEqual(config["expand"]["script"], expected_name)

	def test_load_multiple_profiles(self):
		merger = MockMerger()
		loader = MockLoader(self._tmp_load_dirs, merger)
		config = loader.load(["default", "expand"])
		self.assertIn("network", config[0])
		self.assertIn("expand", config[1])

	def test_include_directive(self):
		merger = MockMerger()
		loader = MockLoader(self._tmp_load_dirs, merger)
		config = loader.load("hasinclude")
		self.assertIn("network", config[0])
		self.assertIn("other", config[1])
