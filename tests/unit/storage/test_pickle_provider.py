import unittest
import os.path
import tempfile

import tuned.storage
import tuned.consts as consts

temp_storage_file = tempfile.TemporaryFile(mode='r')
consts.DEFAULT_STORAGE_FILE = temp_storage_file.name

class StoragePickleProviderTestCase(unittest.TestCase):
	def setUp(self):
		(handle, filename) = tempfile.mkstemp()
		self._temp_filename = filename

	def tearDown(self):
		if os.path.exists(self._temp_filename):
			os.unlink(self._temp_filename)

	def test_default_path(self):
		provider = tuned.storage.PickleProvider(self._temp_filename)
		self.assertEqual(self._temp_filename, provider._path)

		provider = tuned.storage.PickleProvider()
		self.assertEqual(temp_storage_file.name, provider._path)

	def test_memory_persistence(self):
		provider = tuned.storage.PickleProvider(self._temp_filename)

		self.assertEqual("default", provider.get("ns1", "opt1", "default"))
		self.assertIsNone(provider.get("ns2", "opt1"))

		provider.set("ns1", "opt1", "value1")
		provider.set("ns1", "opt2", "value2")
		provider.set("ns2", "opt1", "value3")

		self.assertEqual("value1", provider.get("ns1", "opt1"))
		self.assertEqual("value2", provider.get("ns1", "opt2"))
		self.assertEqual("value3", provider.get("ns2", "opt1"))

		provider.unset("ns1", "opt1")

		self.assertIsNone(provider.get("ns1", "opt1"))
		self.assertEqual("value2", provider.get("ns1", "opt2"))

		provider.clear()

		self.assertIsNone(provider.get("ns1", "opt1"))
		self.assertIsNone(provider.get("ns1", "opt2"))
		self.assertIsNone(provider.get("ns2", "opt1"))

	def test_file_persistence(self):
		provider = tuned.storage.PickleProvider(self._temp_filename)

		provider.load()
		provider.set("ns1", "opt1", "value1")
		provider.set("ns2", "opt2", "value2")
		provider.save()

		del provider
		provider = tuned.storage.PickleProvider(self._temp_filename)

		provider.load()
		self.assertEqual("value1", provider.get("ns1", "opt1"))
		self.assertEqual("value2", provider.get("ns2", "opt2"))
		provider.clear()

		del provider
		provider = tuned.storage.PickleProvider(self._temp_filename)

		provider.load()
		self.assertIsNone(provider.get("ns1", "opt1"))
		self.assertIsNone(provider.get("ns2", "opt2"))

	@classmethod
	def tearDownClass(cls):
		temp_storage_file.close()
