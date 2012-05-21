import unittest
from flexmock import flexmock
import tempfile
import os

import tuned.storage

class StorageFactoryTestCase(unittest.TestCase):
	def test_create(self):
		mock_provider = flexmock()

		factory = tuned.storage.Factory(mock_provider)
		storage_foo = factory.create("foo")
		storage_bar = factory.create("bar")

		self.assertIsInstance(storage_foo, tuned.storage.Storage)
		self.assertIsInstance(storage_bar, tuned.storage.Storage)
		self.assertIsNot(storage_foo, storage_bar)

class StorageStorageTestCase(unittest.TestCase):
	def test_set(self):
		mock_provider = flexmock()
		factory = tuned.storage.Factory(mock_provider)
		storage = factory.create("foo")

		mock_provider.should_receive("set").with_args("foo", "optname", "optval").once
		storage.set("optname", "optval")

	def test_get(self):
		mock_provider = flexmock()
		factory = tuned.storage.Factory(mock_provider)
		storage = factory.create("foo")

		mock_provider.should_receive("get").with_args("foo", "optname", None).and_return(None).once.ordered
		mock_provider.should_receive("get").with_args("foo", "optname", "defval").and_return("defval").once.ordered
		mock_provider.should_receive("get").with_args("foo", "existing", None).and_return("somevalue").once.ordered

		self.assertIsNone(storage.get("optname"))
		self.assertEqual("defval", storage.get("optname", "defval"))
		self.assertEqual("somevalue", storage.get("existing"))

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
		self.assertEqual("/var/run/tuned/save.pickle", provider._path)

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
