import unittest
try:
	from unittest.mock import Mock
	from unittest.mock import call
except ImportError:
	from mock import Mock
	from mock import call
import tuned.storage

class StorageStorageTestCase(unittest.TestCase):
	def test_set(self):
		mock_provider = Mock()
		factory = tuned.storage.Factory(mock_provider)
		storage = factory.create("foo")

		storage.set("optname", "optval")
		mock_provider.set.assert_called_once_with("foo", "optname", "optval")

	def test_get(self):
		mock_provider = Mock()
		mock_provider.get.side_effect = [ None, "defval", "somevalue" ]
		factory = tuned.storage.Factory(mock_provider)
		storage = factory.create("foo")

		self.assertEqual(None, storage.get("optname"))
		self.assertEqual("defval", storage.get("optname", "defval"))
		self.assertEqual("somevalue", storage.get("existing"))

		calls = [
				 call("foo", "optname", None),
				 call("foo", "optname", "defval"),
				 call("foo", "existing", None)
				]

		mock_provider.get.assert_has_calls(calls)
