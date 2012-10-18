import unittest
from flexmock import flexmock
import tuned.storage

class StorageFactoryTestCase(unittest.TestCase):
	def test_create(self):
		mock_provider = flexmock()
		factory = tuned.storage.Factory(mock_provider)

		self.assertEqual(mock_provider, factory.provider)

	def test_create_storage(self):
		mock_provider = flexmock()
		factory = tuned.storage.Factory(mock_provider)

		storage_foo = factory.create("foo")
		storage_bar = factory.create("bar")

		self.assertIsInstance(storage_foo, tuned.storage.Storage)
		self.assertIsInstance(storage_bar, tuned.storage.Storage)
		self.assertIsNot(storage_foo, storage_bar)
