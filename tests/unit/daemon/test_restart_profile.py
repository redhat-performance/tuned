import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from tuned import consts
from tuned.daemon.daemon import Daemon
from tuned.exceptions import TunedException
from tuned.utils.commands import commands
from tuned.utils.global_config import GlobalConfig


class RestartProfileTestCase(unittest.TestCase):
	def setUp(self):
		self.directory = tempfile.TemporaryDirectory()
		self.addCleanup(self.directory.cleanup)
		for key in ("ACTIVE_PROFILE_FILE", "PROFILE_MODE_FILE", "POST_LOADED_PROFILE_FILE"):
			p = patch.object(consts, key, os.path.join(self.directory.name, key))
			p.start()
			self.addCleanup(p.stop)
		config_path = os.path.join(self.directory.name, "tuned-main.conf")
		with open(config_path, "w"):
			pass
		self.config = GlobalConfig(config_path)
		self.loader = Mock()
		self.loader.profile_locator.get_known_names.return_value = [
			"powersave", "balanced", "balanced-battery", "throughput-performance", "custom", "overlay"]
		self.cmd = commands()
		self.cmd.save_active_profile("balanced", True)
		self.cmd.save_post_loaded_profile(None)

	def _fail_initialization(self, profile, manual=True, overlay=None):
		daemon = Daemon(Mock(), self.loader, config=self.config)
		daemon.set_all_profiles(profile, manual, overlay)
		daemon._ensure_bootloader_unit = Mock()
		daemon._full_rollback_required = Mock(return_value=True)
		daemon._unit_manager.create.side_effect = OSError("initialization failed")
		self.assertTrue(daemon.start())
		daemon._thread.join(2)
		self.assertFalse(daemon.is_running())
		daemon._unit_manager.create.assert_called_once()
		self.assertFalse(daemon._profile_applied.is_set())
		return daemon

	def test_restart_loads_last_selected_profile_after_early_failure(self):
		for profile in ("powersave", "balanced-battery", "throughput-performance", "custom balanced"):
			with self.subTest(profile=profile):
				self._fail_initialization(profile, overlay="overlay")
				fresh = Daemon(Mock(), self.loader, config=self.config)
				self.assertEqual(fresh._active_profiles, profile.split())
				self.assertTrue(fresh.manual)
				self.assertEqual(fresh.post_loaded_profile, "overlay")

	@patch("tuned.daemon.daemon.ProfileRecommender.recommend", return_value="balanced-battery")
	def test_restart_preserves_automatic_mode(self, recommend):
		self._fail_initialization("balanced", manual=False)
		fresh = Daemon(Mock(), self.loader, config=self.config)
		self.assertFalse(fresh.manual)
		self.assertEqual(fresh._active_profiles, ["balanced-battery"])
		recommend.assert_called_once_with()

	def test_invalid_selection_does_not_replace_saved_profile(self):
		daemon = Daemon(Mock(), self.loader, config=self.config)
		with self.assertRaises(TunedException):
			daemon.set_profile("does-not-exist", True)
		self.assertEqual(self.cmd.get_active_profile(), ("balanced", True))
