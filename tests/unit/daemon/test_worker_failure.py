import threading
import unittest
from unittest.mock import Mock, patch

from tuned import consts
from tuned.daemon.application import Application
from tuned.daemon.controller import Controller
from tuned.daemon.daemon import Daemon
from tuned.exceptions import TunedException


class WorkerFailureTestCase(unittest.TestCase):
	def setUp(self):
		# Run the real worker/controller with no plugins, sysfs writes, bus
		# connections, profile files or dependence on the host's power policy.
		self.daemon = Daemon.__new__(Daemon)
		self.daemon._init_threads()
		self.daemon._profile = Mock(units={})
		self.daemon._profile.name = "throughput-performance"
		self.daemon._active_profiles = ["throughput-performance"]
		self.daemon._post_loaded_profile = "custom-overlay"
		self.daemon._manual = True
		self.daemon._daemon = True
		self.daemon._dynamic_tuning = True
		self.daemon._sleep_interval = 0.01
		self.daemon._sleep_cycles = 1
		self.daemon._rollback = consts.CFG_DEF_ROLLBACK
		self.daemon._unit_manager = Mock()
		self.daemon._cmd = Mock()
		self.daemon._cmd.wait.side_effect = lambda event, interval: event.wait(interval)
		self.daemon._ensure_bootloader_unit = Mock()
		self.daemon._full_rollback_required = Mock(return_value=True)
		self.config = Mock()
		self.config.get_int.return_value = 0
		self.config.get_bool.return_value = True
		self.controller = Controller(self.daemon, self.config)
		self.daemon._application = Mock(controller=self.controller)
		self.signals = []
		self.signal = self._patch("tuned.exports.send_signal")
		self.signal.side_effect = lambda *args: self.signals.append(args)
		self._patch("tuned.exports.start")
		self._patch("tuned.exports.stop")
		self._patch("tuned.exports.period_check")
		self.worker_log = self._patch("tuned.daemon.daemon.log")
		# Bound a regression on the original code, whose controller keeps
		# waiting forever after the worker exits. This is only a test deadline.
		self.deadline = threading.Timer(2, self.controller.terminate)
		self.deadline.start()
		self.addCleanup(self._stop_threads)

	def _patch(self, name):
		p = patch(name)
		result = p.start()
		self.addCleanup(p.stop)
		return result

	def _stop_threads(self):
		self.deadline.cancel()
		self.deadline.join()
		self.daemon._terminate.set()
		if self.daemon._thread is not None:
			self.daemon._thread.join(2)
			self.assertFalse(self.daemon._thread.is_alive())

	def _assert_failure(self, message):
		with self.assertRaisesRegex(TunedException, message):
			self.controller.run()
		self.assertFalse(self.daemon.is_running())
		self.assertFalse(self.daemon._profile_applied.is_set())
		self.assertFalse(self.daemon._sighup_processing.is_set())
		self.assertIn(message, self.daemon.thread_error)
		self.worker_log.exception.assert_any_call(self.daemon.thread_error)
		self.assertEqual(self.signals[-1],
			(consts.SIGNAL_PROFILE_CHANGED, "throughput-performance", False,
			 self.daemon.thread_error))

	def test_initialization_failure_reaches_controller(self):
		self.daemon._unit_manager.create.side_effect = OSError("filter too large")
		self.daemon._sighup_processing.set()
		self._assert_failure("filter too large")
		self.assertEqual(len(self.signals), 1)
		self.daemon._unit_manager.start_tuning.assert_not_called()
		# The selection must survive initialization failure for the next
		# process, without falsely reporting that it was applied.
		self.assertEqual(self.daemon._active_profiles, ["throughput-performance"])
		self.assertTrue(self.daemon.manual)
		self.assertEqual(self.daemon.post_loaded_profile, "custom-overlay")
		self.daemon._cmd.save_active_profile.assert_called_once_with("throughput-performance", True)
		self.daemon._cmd.save_post_loaded_profile.assert_called_once_with("custom-overlay")
		self.daemon._unit_manager.destroy_all.assert_called_once_with()

	def test_dynamic_tuning_failure_clears_applied_state(self):
		self.daemon._unit_manager.update_tuning.side_effect = RuntimeError("update failed")
		self._assert_failure("update failed")
		self.assertTrue(self.signals[0][2])
		self.daemon._cmd.save_active_profile.assert_called_once_with("throughput-performance", True)
		self.daemon._unit_manager.stop_tuning.assert_called_once_with(consts.ROLLBACK_FULL)
		self.daemon._unit_manager.destroy_all.assert_called_once_with()

	def test_failure_stops_plugin_threads(self):
		plugin_stop = threading.Event()
		plugin_thread = threading.Thread(target=plugin_stop.wait)
		self.daemon._unit_manager.start_tuning.side_effect = plugin_thread.start
		def stop_plugin(rollback):
			plugin_stop.set()
			plugin_thread.join(1)
		self.addCleanup(lambda: (plugin_stop.set(), plugin_thread.join(1)))
		self.daemon._unit_manager.stop_tuning.side_effect = stop_plugin
		self.daemon._unit_manager.update_tuning.side_effect = RuntimeError("update failed")
		self._assert_failure("update failed")
		self.assertFalse(plugin_thread.is_alive())

	def test_unapply_failure_still_destroys_plugins(self):
		self.signal.side_effect = lambda *args: (self.signals.append(args), self.controller.terminate())
		self.daemon._unit_manager.stop_tuning.side_effect = RuntimeError("unapply failed")
		self._assert_failure("unapply failed")
		self.daemon._unit_manager.destroy_all.assert_called_once_with()

	def test_failure_preserves_automatic_mode_and_rollback_policy(self):
		self.daemon._manual = False
		self.daemon._rollback = "not_on_exit"
		self.daemon._unit_manager.update_tuning.side_effect = RuntimeError("update failed")
		self._assert_failure("update failed")
		self.daemon._cmd.save_active_profile.assert_called_once_with("throughput-performance", False)
		self.daemon._unit_manager.stop_tuning.assert_called_once_with(consts.ROLLBACK_NONE)
		self.assertFalse(self.daemon.manual)

	def test_teardown_failure_is_fatal(self):
		self.signal.side_effect = lambda *args: (self.signals.append(args), self.controller.terminate())
		self.daemon._unit_manager.destroy_all.side_effect = RuntimeError("cleanup failed")
		self._assert_failure("cleanup failed")

	def test_broken_failure_notification_still_terminates(self):
		self.daemon._unit_manager.create.side_effect = OSError("original failure")
		self.signal.side_effect = RuntimeError("exporter unavailable")
		with self.assertRaisesRegex(TunedException, "original failure"):
			self.controller.run()
		self.assertFalse(self.daemon.is_running())
		self.worker_log.exception.assert_any_call("Cannot report tuning thread failure to clients")

	def test_failed_worker_cannot_restart_in_same_process(self):
		self.daemon._unit_manager.create.side_effect = OSError("initialization failed")
		self._assert_failure("initialization failed")
		with self.assertRaisesRegex(TunedException, "initialization failed"):
			self.daemon.start()
		self.assertEqual(self.daemon._unit_manager.create.call_count, 1)

	def test_intentional_stop_is_successful(self):
		self.signal.side_effect = lambda *args: (self.signals.append(args), self.controller.terminate())
		self.controller.run()
		self.assertIsNone(self.daemon.thread_error)
		self.assertEqual(len(self.signals), 1)
		self.assertTrue(self.signals[0][2])
		self.daemon._unit_manager.stop_tuning.assert_called_once_with(consts.ROLLBACK_FULL)
		self.daemon._unit_manager.destroy_all.assert_called_once_with()

	def test_profile_switch_can_start_another_worker(self):
		applied = threading.Event()
		self.signal.side_effect = lambda *args: applied.set()
		self.assertTrue(self.daemon.start())
		self.assertTrue(applied.wait(1))
		self.assertTrue(self.daemon.stop(profile_switch=True))
		self.assertIsNone(self.daemon.thread_error)
		applied.clear()
		self.assertTrue(self.daemon.start())
		self.assertTrue(applied.wait(1))
		self.assertTrue(self.daemon.stop())
		self.assertEqual(self.daemon._unit_manager.create.call_count, 2)

	def test_disabled_profile_is_not_worker_failure(self):
		self.daemon._profile = None
		self.controller._cmd.wait = Mock(side_effect=lambda event, interval: (event.set(), True)[1])
		self.controller.run()
		self.assertIsNone(self.daemon.thread_error)
		self.assertEqual(self.signals, [])

	def test_one_shot_failure_reaches_caller(self):
		self.daemon._daemon = False
		self.config.get_bool.return_value = False
		self.daemon._unit_manager.create.side_effect = OSError("one-shot failed")
		self._assert_failure("one-shot failed")

	def test_one_shot_success(self):
		self.daemon._daemon = False
		self.config.get_bool.return_value = False
		self.controller.run()
		self.assertIsNone(self.daemon.thread_error)
		self.daemon._unit_manager.stop_tuning.assert_not_called()
		self.daemon._unit_manager.destroy_all.assert_called_once_with()


class ApplicationCleanupTestCase(unittest.TestCase):
	def setUp(self):
		self.app = Application.__new__(Application)
		self.app.config = Mock()
		self.app.config.get_bool.return_value = True
		self.app._controller = Mock()
		self.app._pid_file = "/unused/test.pid"
		self.app._delete_pid_file = Mock()

	@patch("tuned.exports.stop")
	def test_worker_failure_closes_exports_and_removes_pid(self, stop):
		self.app._controller.run.side_effect = TunedException("worker failed")
		with self.assertRaisesRegex(TunedException, "worker failed"):
			self.app.run(False)
		stop.assert_called_once_with()
		self.app._delete_pid_file.assert_called_once_with()

	@patch("tuned.exports.stop", side_effect=RuntimeError("export cleanup failed"))
	def test_export_cleanup_failure_still_removes_pid(self, stop):
		with self.assertRaisesRegex(RuntimeError, "export cleanup failed"):
			self.app.run(False)
		self.app._delete_pid_file.assert_called_once_with()
