import threading
import unittest
from unittest.mock import Mock, patch

from tuned import consts
from tuned.plugins.plugin_scheduler import SchedulerPlugin


class SchedulerCleanupTestCase(unittest.TestCase):
	def setUp(self):
		self.plugin = SchedulerPlugin.__new__(SchedulerPlugin)

	def test_cleanup_stops_thread_without_rolling_back_tuning(self):
		instance = Mock()
		instance._terminate = threading.Event()
		instance._thread = threading.Thread(target=instance._terminate.wait)
		instance._evlist = None
		instance._thread.start()
		self.addCleanup(lambda: (instance._terminate.set(), instance._thread.join(1)))
		self.plugin._instance_unapply_static = Mock()
		self.plugin._instance_unapply_dynamic = Mock()

		# The configured no-rollback policy intentionally skips unapply.
		self.plugin.instance_unapply_tuning(instance, consts.ROLLBACK_NONE)
		self.assertTrue(instance._thread.is_alive())
		self.plugin._instance_cleanup(instance)

		self.assertFalse(instance._thread.is_alive())
		self.plugin._instance_unapply_static.assert_not_called()
		self.plugin._instance_unapply_dynamic.assert_not_called()

	def test_cleanup_before_initialization_is_safe(self):
		# A real instance has neither attribute if initialization was never
		# reached. Mock() would synthesize them and hide that condition.
		class UninitializedInstance(object):
			pass
		self.plugin._instance_cleanup(UninitializedInstance())

	@patch("tuned.plugins.plugin_scheduler.os.close")
	def test_thread_stops_before_perf_descriptors_close(self, close):
		instance = Mock()
		instance._terminate = threading.Event()
		instance._thread = threading.Thread(target=instance._terminate.wait)
		instance._thread.start()
		self.addCleanup(lambda: (instance._terminate.set(), instance._thread.join(1)))
		fd = Mock()
		fd.name = 123
		instance._evlist.get_pollfd.return_value = [fd]
		close.side_effect = lambda unused: self.assertFalse(instance._thread.is_alive())

		self.plugin._instance_cleanup(instance)

		close.assert_called_once_with(123)
