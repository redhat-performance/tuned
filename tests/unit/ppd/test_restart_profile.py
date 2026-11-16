import os
import tempfile
import unittest
from unittest.mock import Mock, patch
import dbus

from tuned.ppd.controller import Controller
from tuned.utils.commands import commands


class PPDRestartProfileTestCase(unittest.TestCase):
	def test_new_choice_is_saved_before_a_failed_switch_request(self):
		with tempfile.TemporaryDirectory() as directory:
			path = os.path.join(directory, "ppd_base_profile")
			with patch("tuned.ppd.controller.PPD_BASE_PROFILE_FILE", path):
				for error in (False, dbus.exceptions.DBusException("backend disconnected")):
					with self.subTest(error=error):
						with open(path, "w") as f:
							f.write("balanced\n")
						c = Controller.__new__(Controller)
						c._cmd = commands()
						c._base_profile = "balanced"
						c._on_battery = False
						c._profile_holds = Mock()
						c._config = Mock()
						c._config.ppd_to_tuned.keys.return_value = ["performance", "balanced", "power-saver"]
						def failed_switch(profile):
							with open(path) as f:
								self.assertEqual(f.read(), profile + "\n")
							if isinstance(error, Exception):
								raise error
							return error
						c.switch_profile = failed_switch
						with self.assertRaises(dbus.exceptions.DBusException):
							c.set_active_profile("performance", None)
						self.assertEqual(c._load_base_profile(), "performance")

	def test_invalid_desktop_choice_is_not_saved(self):
		c = Controller.__new__(Controller)
		c._config = Mock()
		c._config.ppd_to_tuned.keys.return_value = ["performance", "balanced", "power-saver"]
		c._on_battery = False
		c._save_base_profile = Mock()
		with self.assertRaises(dbus.exceptions.DBusException):
			c.set_active_profile("invalid", None)
		c._save_base_profile.assert_not_called()

	@patch("tuned.ppd.controller.exports.property_changed")
	@patch("tuned.ppd.controller.PPDConfig")
	def test_restart_restores_saved_desktop_choice_on_ac_and_battery(self, config_cls, changed):
		with tempfile.TemporaryDirectory() as directory:
			path = os.path.join(directory, "ppd_base_profile")
			with patch("tuned.ppd.controller.PPD_BASE_PROFILE_FILE", path):
				for profile in ("performance", "balanced", "power-saver"):
					for battery in (False, True):
						with self.subTest(profile=profile, battery=battery):
							with open(path, "w") as f:
								f.write(profile + "\n")
							c = Controller.__new__(Controller)
							c._cmd = commands()
							c._tuned_interface = Mock()
							c._tuned_interface.active_profile.return_value = "old-profile"
							c._tuned_interface.switch_profile.return_value = (True, "OK")
							c._on_battery = battery
							c._setup_battery_signaling = Mock()
							c._setup_inotify = Mock()
							c.check_performance_degraded = Mock()
							c._get_recommend_profile = Mock(return_value="balanced")
							mapped = profile + ("-dc" if battery else "-ac")
							config_cls.return_value.ppd_to_tuned.get.return_value = mapped
							c.initialize()
							self.assertEqual(c.base_profile, profile)
							self.assertEqual(c._active_profile, profile)
							c._tuned_interface.switch_profile.assert_called_once_with(mapped)
							config_cls.return_value.ppd_to_tuned.get.assert_called_with(profile, battery)
							c._get_recommend_profile.assert_not_called()
							with open(path) as f:
								self.assertEqual(f.read(), profile + "\n")
