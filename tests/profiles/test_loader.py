import unittest
import tempfile
import shutil
import os.path
import tuned.profiles.loader

# DI: return config itself instead of the profile
class TestLoader(tuned.profiles.loader.Loader):
	def _create_profile(self, profile_name, config):
		return config

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
		tuned.profiles.loader.Loader()
		tuned.profiles.loader.Loader([])
		tuned.profiles.loader.Loader(["/tmp"])
		tuned.profiles.loader.Loader(["/foo", "/bar"])

	def test_init_wrong_type(self):
		with self.assertRaises(TypeError):
			tuned.profiles.loader.Loader(False)

	def test_init_extra_params(self):
		with self.assertRaises(TypeError):
			tuned.profiles.loader.Loader([], "extra")

	def test_default_load_directories(self):
		loader = tuned.profiles.loader.Loader()

		# order is important
		self.assertEqual(len(loader.load_directories), 2)
		self.assertEqual(loader.load_directories[0], "/var/lib/tuned")
		self.assertEqual(loader.load_directories[1], "/etc/tuned")

	def test_add_directory(self):
		loader = tuned.profiles.loader.Loader([])
		self.assertEqual(len(loader.load_directories), 0);

		loader.add_directory("/a")
		self.assertEqual(len(loader.load_directories), 1);

		loader.add_directory("/b")
		self.assertEqual(len(loader.load_directories), 2);

		self.assertEqual(loader.load_directories[0], "/a")
		self.assertEqual(loader.load_directories[1], "/b")

	def test_load(self):
		loader = TestLoader(self._tmp_load_dirs)
		default_config = loader.load("default")

		self.assertIn("main", default_config)
		self.assertIn("network", default_config)
		self.assertIn("disk", default_config)

		self.assertNotIn("type", default_config["main"])
		self.assertEquals(default_config["network"]["type"], "net")
		self.assertEquals(default_config["disk"]["type"], "disk")

		self.assertEquals(len(default_config["main"]), 0);
		self.assertEquals(len(default_config["network"]), 2);
		self.assertEquals(len(default_config["disk"]), 2);

		self.assertEquals(default_config["network"]["devices"], "em*")
		self.assertEquals(default_config["disk"]["enabled"], "false") # TODO: improve parser

	def test_load_empty(self):
		loader = TestLoader(self._tmp_load_dirs)
		empty_config = loader.load("empty")
		self.assertEquals(empty_config, {})

	def test_load_invalid(self):
		loader = TestLoader(self._tmp_load_dirs)
		with self.assertRaises(tuned.profiles.exceptions.InvalidProfileException):
			invalid_config = loader.load("invalid")

	def test_load_nonexistent(self):
		loader = TestLoader(self._tmp_load_dirs)
		with self.assertRaises(tuned.profiles.exceptions.InvalidProfileException):
			config = loader.load("nonexistent")

	def test_load_order(self):
		loader = TestLoader(self._tmp_load_dirs)
		custom_config = loader.load("custom")
		self.assertEquals(custom_config["custom"]["type"], "two")

	def test_default_load(self):
		loader = tuned.profiles.loader.Loader(self._tmp_load_dirs)
		config = loader.load("empty")
		self.assertIs(type(config), tuned.profiles.profile.Profile)

	def test_script_expand_names(self):
		loader = TestLoader(self._tmp_load_dirs)
		config = loader.load("expand")
		expected_name = os.path.join(self._tmp_load_dirs[0], "expand", "runme.sh")
		self.assertEqual(config["expand"]["script"], expected_name)

	def test_load_multiple_profiles(self):
		loader = TestLoader(self._tmp_load_dirs)
		config = loader.load(["default", "expand"])
		self.assertIn("network", config)
		self.assertIn("expand", config)

	def test_include_directive(self):
		loader = TestLoader(self._tmp_load_dirs)
		config = loader.load("hasinclude")
		self.assertIn("network", config)
		self.assertIn("other", config)
