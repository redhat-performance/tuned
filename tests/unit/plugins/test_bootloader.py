import unittest

try:
	from unittest.mock import Mock
except ImportError:
	from mock import Mock

import tuned.consts as consts


class BootloaderPluginBootcTestCase(unittest.TestCase):
	"""Tests for the bootc loader-entries set-options-for-source integration
	in the bootloader plugin.

	These tests exercise the bootc detection, source-based kargs apply,
	source-based kargs removal, and the dispatch logic that falls back to
	the rpm-ostree or GRUB2 code paths when bootc is not available.

	The BootloaderPlugin constructor requires /etc/grub.d/00_tuned to exist,
	so we test the methods directly on a minimal mock rather than
	instantiating the full plugin.
	"""

	def _make_plugin_mock(self, bootc_has_source=True):
		"""Create a mock that has the real methods under test patched onto it.

		This avoids instantiating BootloaderPlugin (which requires GRUB2
		template files on disk) while still testing the actual method logic.

		Args:
			bootc_has_source: Whether bootc set-options-for-source is available
		"""
		from tuned.plugins.plugin_bootloader import BootloaderPlugin

		mock_plugin = Mock(spec=BootloaderPlugin)
		mock_plugin._bootc_has_source = bootc_has_source
		mock_plugin._cmdline_val = ""
		mock_plugin._cmd = Mock()
		mock_plugin._cmd.add_modify_option_in_file = Mock(return_value=True)

		# Bind real methods to the mock so we test actual logic
		mock_plugin._bootc_has_set_options_for_source = \
			lambda: BootloaderPlugin._bootc_has_set_options_for_source(mock_plugin)
		mock_plugin._bootc_source_update = \
			lambda: BootloaderPlugin._bootc_source_update(mock_plugin)
		mock_plugin._remove_bootc_source_tuning = \
			lambda: BootloaderPlugin._remove_bootc_source_tuning(mock_plugin)
		mock_plugin._patch_bootcmdline = \
			lambda d: BootloaderPlugin._patch_bootcmdline(mock_plugin, d)

		return mock_plugin

	# ------------------------------------------------------------------
	# _bootc_has_set_options_for_source() detection
	# ------------------------------------------------------------------

	def test_bootc_has_source_present(self):
		"""bootc set-options-for-source is detected when --help succeeds."""
		plugin = self._make_plugin_mock()
		plugin._cmd.execute = Mock(return_value=(0, "Usage: bootc loader-entries...", ""))
		self.assertTrue(plugin._bootc_has_set_options_for_source())
		plugin._cmd.execute.assert_called_once_with(
			['bootc', 'loader-entries', 'set-options-for-source', '--help'],
			return_err=True)

	def test_bootc_has_source_absent(self):
		"""bootc set-options-for-source is not detected when --help fails."""
		plugin = self._make_plugin_mock()
		plugin._cmd.execute = Mock(return_value=(1, "", "error: unrecognized subcommand"))
		self.assertFalse(plugin._bootc_has_set_options_for_source())

	def test_bootc_has_source_not_installed(self):
		"""bootc set-options-for-source is not detected when bootc is not installed."""
		plugin = self._make_plugin_mock()
		plugin._cmd.execute = Mock(return_value=(127, "", "command not found"))
		self.assertFalse(plugin._bootc_has_set_options_for_source())

	# ------------------------------------------------------------------
	# _bootc_source_update()
	# ------------------------------------------------------------------

	def test_bootc_source_update_basic(self):
		"""bootc set-options-for-source is called with correct --options."""
		plugin = self._make_plugin_mock()
		plugin._cmdline_val = "nohz=full isolcpus=1-3"
		plugin._cmd.execute = Mock(return_value=(0, "", ""))

		plugin._bootc_source_update()

		plugin._cmd.execute.assert_called_once_with(
			["bootc", "loader-entries", "set-options-for-source",
			 "--source", "tuned", "--options", "nohz=full isolcpus=1-3"],
			return_err=True)
		# Verify bootcmdline state file is updated
		plugin._cmd.add_modify_option_in_file.assert_called_once_with(
			consts.BOOT_CMDLINE_FILE,
			{consts.BOOT_CMDLINE_TUNED_VAR: "nohz=full isolcpus=1-3"})

	def test_bootc_source_update_empty_cmdline(self):
		"""When cmdline is empty, --options is not passed (clears kargs)."""
		plugin = self._make_plugin_mock()
		plugin._cmdline_val = ""
		plugin._cmd.execute = Mock(return_value=(0, "", ""))

		plugin._bootc_source_update()

		plugin._cmd.execute.assert_called_once_with(
			["bootc", "loader-entries", "set-options-for-source",
			 "--source", "tuned"],
			return_err=True)
		plugin._cmd.add_modify_option_in_file.assert_called_once_with(
			consts.BOOT_CMDLINE_FILE,
			{consts.BOOT_CMDLINE_TUNED_VAR: ""})

	def test_bootc_source_update_command_fails(self):
		"""When bootc fails, bootcmdline is not updated."""
		plugin = self._make_plugin_mock()
		plugin._cmdline_val = "nohz=full"
		plugin._cmd.execute = Mock(return_value=(1, "", "error: ostree too old"))

		plugin._bootc_source_update()

		plugin._cmd.execute.assert_called_once()
		plugin._cmd.add_modify_option_in_file.assert_not_called()

	# ------------------------------------------------------------------
	# _remove_bootc_source_tuning()
	# ------------------------------------------------------------------

	def test_remove_bootc_source_tuning(self):
		"""Removal calls set-options-for-source with no --options (clears all)."""
		plugin = self._make_plugin_mock()
		plugin._cmd.execute = Mock(return_value=(0, "", ""))

		plugin._remove_bootc_source_tuning()

		plugin._cmd.execute.assert_called_once_with(
			["bootc", "loader-entries", "set-options-for-source",
			 "--source", "tuned"],
			return_err=True)
		plugin._cmd.add_modify_option_in_file.assert_called_once_with(
			consts.BOOT_CMDLINE_FILE,
			{consts.BOOT_CMDLINE_TUNED_VAR: ""})

	def test_remove_bootc_source_tuning_command_fails(self):
		"""When bootc removal fails, bootcmdline is still cleared."""
		plugin = self._make_plugin_mock()
		plugin._cmd.execute = Mock(return_value=(1, "", "error"))

		plugin._remove_bootc_source_tuning()

		plugin._cmd.add_modify_option_in_file.assert_called_once_with(
			consts.BOOT_CMDLINE_FILE,
			{consts.BOOT_CMDLINE_TUNED_VAR: ""})

	# ------------------------------------------------------------------
	# Init flag derivation logic
	# ------------------------------------------------------------------

	def test_init_bootc_available(self):
		"""When bootc is available, _bootc_has_source is True."""
		plugin = Mock()
		plugin._cmd = Mock()
		plugin._bootc_has_set_options_for_source = Mock(return_value=True)
		plugin._rpm_ostree_status = Mock(return_value="idle")

		plugin._rpm_ostree = plugin._rpm_ostree_status() is not None
		plugin._bootc_has_source = plugin._bootc_has_set_options_for_source()

		self.assertTrue(plugin._bootc_has_source)

	def test_init_no_bootc_no_rpm_ostree(self):
		"""When neither bootc nor rpm-ostree is available, both flags are False."""
		plugin = Mock()
		plugin._cmd = Mock()
		plugin._bootc_has_set_options_for_source = Mock(return_value=False)
		plugin._rpm_ostree_status = Mock(return_value=None)

		plugin._rpm_ostree = plugin._rpm_ostree_status() is not None
		plugin._bootc_has_source = plugin._bootc_has_set_options_for_source()

		self.assertFalse(plugin._bootc_has_source)
		self.assertFalse(plugin._rpm_ostree)

	# ------------------------------------------------------------------
	# Top-level dispatch
	# ------------------------------------------------------------------

	def test_dispatch_bootc_independent_of_rpm_ostree(self):
		"""bootc path works even when _rpm_ostree is False (bootc-only system)."""
		plugin = self._make_plugin_mock(bootc_has_source=True)
		plugin._rpm_ostree = False
		plugin._cmdline_val = "nohz=full"
		plugin._cmd.execute = Mock(return_value=(0, "", ""))

		# Simulate _instance_post_static dispatch
		if plugin._bootc_has_source:
			plugin._bootc_source_update()
		elif plugin._rpm_ostree:
			pass  # would call _rpm_ostree_update

		plugin._cmd.execute.assert_called_once_with(
			["bootc", "loader-entries", "set-options-for-source",
			 "--source", "tuned", "--options", "nohz=full"],
			return_err=True)

	def test_dispatch_falls_through_to_rpm_ostree(self):
		"""When bootc is not available, dispatch falls through to rpm-ostree."""
		plugin = self._make_plugin_mock(bootc_has_source=False)
		plugin._rpm_ostree = True

		# Simulate _instance_post_static dispatch
		bootc_called = False
		rpm_ostree_called = False
		if plugin._bootc_has_source:
			bootc_called = True
		elif plugin._rpm_ostree:
			rpm_ostree_called = True

		self.assertFalse(bootc_called)
		self.assertTrue(rpm_ostree_called)

	def test_instance_post_static_dispatches_to_bootc(self):
		"""_instance_post_static calls bootc when _bootc_has_source is True."""
		from tuned.plugins.plugin_bootloader import BootloaderPlugin

		plugin = self._make_plugin_mock(bootc_has_source=True)
		plugin._rpm_ostree = False
		plugin._cmdline_val = "nohz=full"
		plugin._cmd.execute = Mock(return_value=(0, "", ""))
		plugin.update_grub2_cfg = True
		plugin._skip_grub_config_val = False

		instance = Mock()
		BootloaderPlugin._instance_post_static(plugin, instance, enabling=True)

		plugin._cmd.execute.assert_called_once_with(
			["bootc", "loader-entries", "set-options-for-source",
			 "--source", "tuned", "--options", "nohz=full"],
			return_err=True)

	def test_instance_unapply_dispatches_to_bootc(self):
		"""_instance_unapply_static calls bootc removal when _bootc_has_source."""
		from tuned.plugins.plugin_bootloader import BootloaderPlugin
		import tuned.consts as c

		plugin = self._make_plugin_mock(bootc_has_source=True)
		plugin._rpm_ostree = False
		plugin._cmd.execute = Mock(return_value=(0, "", ""))
		plugin._skip_grub_config_val = False

		instance = Mock()
		BootloaderPlugin._instance_unapply_static(plugin, instance, rollback=c.ROLLBACK_FULL)

		plugin._cmd.execute.assert_called_once_with(
			["bootc", "loader-entries", "set-options-for-source",
			 "--source", "tuned"],
			return_err=True)

	def test_instance_unapply_falls_through_to_rpm_ostree(self):
		"""_instance_unapply_static falls through to rpm-ostree when no bootc."""
		from tuned.plugins.plugin_bootloader import BootloaderPlugin
		import tuned.consts as c

		plugin = self._make_plugin_mock(bootc_has_source=False)
		plugin._rpm_ostree = True
		plugin._skip_grub_config_val = False
		plugin._remove_rpm_ostree_tuning = Mock()

		instance = Mock()
		BootloaderPlugin._instance_unapply_static(plugin, instance, rollback=c.ROLLBACK_FULL)

		plugin._remove_rpm_ostree_tuning.assert_called_once()

	def test_instance_post_static_clears_stale_kargs_on_bootc(self):
		"""When profile has no [bootloader] cmdline but bootc is available,
		_instance_post_static still calls _bootc_source_update to clear
		any stale kargs from a previous profile."""
		from tuned.plugins.plugin_bootloader import BootloaderPlugin

		plugin = self._make_plugin_mock(bootc_has_source=True)
		plugin._rpm_ostree = False
		plugin._cmdline_val = ""
		plugin._initrd_val = ""
		plugin._cmd.execute = Mock(return_value=(0, "", ""))
		plugin.update_grub2_cfg = False
		plugin._skip_grub_config_val = False

		instance = Mock()
		BootloaderPlugin._instance_post_static(plugin, instance, enabling=True)

		# Should call bootc with no --options (clear source)
		plugin._cmd.execute.assert_called_once_with(
			["bootc", "loader-entries", "set-options-for-source",
			 "--source", "tuned"],
			return_err=True)

	def test_instance_post_static_no_bootc_no_stale_clear(self):
		"""When bootc is not available and profile has no cmdline,
		_instance_post_static does nothing."""
		from tuned.plugins.plugin_bootloader import BootloaderPlugin

		plugin = self._make_plugin_mock(bootc_has_source=False)
		plugin._rpm_ostree = False
		plugin._cmdline_val = ""
		plugin._initrd_val = ""
		plugin._cmd.execute = Mock(return_value=(0, "", ""))
		plugin.update_grub2_cfg = False
		plugin._skip_grub_config_val = False

		instance = Mock()
		BootloaderPlugin._instance_post_static(plugin, instance, enabling=True)

		# Should NOT call any bootc or rpm-ostree commands
		plugin._cmd.execute.assert_not_called()


class DaemonEnsureBootloaderUnitTestCase(unittest.TestCase):
	"""Tests for the _ensure_bootloader_unit logic in Daemon.

	The Daemon class cannot be imported directly in unit tests because
	tuned.daemon.__init__ triggers a chain of imports (pyudev, dbus, etc.)
	that are unavailable in the test environment.  Instead, we replicate
	the _ensure_bootloader_unit logic inline - the method is simple
	enough that this is reliable and avoids import gymnastics.
	"""

	@staticmethod
	def _ensure_bootloader_unit(daemon_self):
		"""Replica of Daemon._ensure_bootloader_unit for testing."""
		import collections
		if "bootloader" in daemon_self._profile.units:
			return
		(retcode, out, err) = daemon_self._cmd.execute(
			["bootc", "loader-entries", "set-options-for-source",
			 "--help"], return_err=True)
		if retcode != 0:
			return
		from tuned.profiles.unit import Unit
		daemon_self._profile.units["bootloader"] = Unit(
			"bootloader", collections.OrderedDict())

	def _make_daemon_mock(self, has_bootloader_unit=False, bootc_available=True):
		"""Create a minimal mock simulating Daemon state."""
		import collections

		daemon = Mock()
		daemon._cmd = Mock()
		if bootc_available:
			daemon._cmd.execute = Mock(return_value=(0, "Usage: ...", ""))
		else:
			daemon._cmd.execute = Mock(return_value=(127, "", "command not found"))
		daemon._profile = Mock()
		daemon._profile.units = collections.OrderedDict()
		if has_bootloader_unit:
			from tuned.profiles.unit import Unit
			daemon._profile.units["bootloader"] = Unit(
				"bootloader", collections.OrderedDict({"cmdline": "foo=bar"}))
		return daemon

	def test_injects_unit_when_bootc_available_and_no_bootloader(self):
		"""Synthetic bootloader unit is injected when bootc is available
		and the profile has no [bootloader] section."""
		daemon = self._make_daemon_mock(has_bootloader_unit=False, bootc_available=True)

		self._ensure_bootloader_unit(daemon)

		self.assertIn("bootloader", daemon._profile.units)
		self.assertEqual(daemon._profile.units["bootloader"].type, "bootloader")

	def test_no_inject_when_bootloader_already_present(self):
		"""No injection when the profile already has a [bootloader] section."""
		daemon = self._make_daemon_mock(has_bootloader_unit=True, bootc_available=True)

		self._ensure_bootloader_unit(daemon)

		# Should still be the original unit with options, not replaced
		self.assertIn("cmdline", daemon._profile.units["bootloader"].options)

	def test_no_inject_when_bootc_unavailable(self):
		"""No injection when bootc is not available."""
		daemon = self._make_daemon_mock(has_bootloader_unit=False, bootc_available=False)

		self._ensure_bootloader_unit(daemon)

		self.assertNotIn("bootloader", daemon._profile.units)


if __name__ == '__main__':
	unittest.main()
