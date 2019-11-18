import unittest
from flexmock import flexmock
import tuned.storage

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

