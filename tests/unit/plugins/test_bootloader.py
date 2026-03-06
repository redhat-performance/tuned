import unittest

try:
	from unittest.mock import Mock, patch, call
except ImportError:
	from mock import Mock, patch, call

import tuned.consts as consts


class BootloaderPluginSourceTestCase(unittest.TestCase):
	"""Tests for the rpm-ostree --source=tuned integration in the bootloader plugin.

	These tests exercise the --source detection, source-based kargs apply,
	source-based kargs removal, and the dispatch logic that falls back to
	the legacy code path when --source is not available.

	The BootloaderPlugin constructor requires /etc/grub.d/00_tuned to exist,
	so we test the methods directly on a minimal mock rather than
	instantiating the full plugin.
	"""

	def _make_plugin_mock(self, has_source=True, rpm_ostree_idle=True):
		"""Create a mock that has the real methods under test patched onto it.

		This avoids instantiating BootloaderPlugin (which requires GRUB2
		template files on disk) while still testing the actual method logic.
		"""
		from tuned.plugins.plugin_bootloader import BootloaderPlugin

		mock_plugin = Mock(spec=BootloaderPlugin)
		mock_plugin._rpm_ostree_has_source = has_source
		mock_plugin._cmdline_val = ""
		mock_plugin._cmd = Mock()
		mock_plugin._cmd.add_modify_option_in_file = Mock(return_value=True)

		# Make _wait_till_rpm_ostree_idle return the desired value
		mock_plugin._wait_till_rpm_ostree_idle = Mock(return_value=rpm_ostree_idle)

		# Bind real methods to the mock so we test actual logic
		mock_plugin._rpm_ostree_has_source_flag = \
			lambda: BootloaderPlugin._rpm_ostree_has_source_flag(mock_plugin)
		mock_plugin._rpm_ostree_source_update = \
			lambda: BootloaderPlugin._rpm_ostree_source_update(mock_plugin)
		mock_plugin._remove_rpm_ostree_source_tuning = \
			lambda: BootloaderPlugin._remove_rpm_ostree_source_tuning(mock_plugin)
		mock_plugin._rpm_ostree_update = \
			lambda: BootloaderPlugin._rpm_ostree_update(mock_plugin)
		mock_plugin._remove_rpm_ostree_tuning = \
			lambda: BootloaderPlugin._remove_rpm_ostree_tuning(mock_plugin)
		mock_plugin._patch_bootcmdline = \
			lambda d: BootloaderPlugin._patch_bootcmdline(mock_plugin, d)

		return mock_plugin

	# ------------------------------------------------------------------
	# _rpm_ostree_has_source_flag() detection
	# ------------------------------------------------------------------

	def test_has_source_flag_present(self):
		"""--source flag is detected when present in rpm-ostree kargs --help."""
		plugin = self._make_plugin_mock()
		help_text = (
			"Usage:\n"
			"  rpm-ostree kargs [OPTION...]\n\n"
			"  --append=KEY=VALUE     Append kernel argument\n"
			"  --source=NAME          Track kargs ownership by source name\n"
			"  --delete=KEY=VALUE     Delete a kernel argument\n"
		)
		plugin._cmd.execute = Mock(return_value=(0, help_text, ""))
		self.assertTrue(plugin._rpm_ostree_has_source_flag())
		plugin._cmd.execute.assert_called_once_with(
			['rpm-ostree', 'kargs', '--help'], return_err=True)

	def test_has_source_flag_absent(self):
		"""--source flag is not detected when absent from rpm-ostree kargs --help."""
		plugin = self._make_plugin_mock()
		help_text = (
			"Usage:\n"
			"  rpm-ostree kargs [OPTION...]\n\n"
			"  --append=KEY=VALUE     Append kernel argument\n"
			"  --delete=KEY=VALUE     Delete a kernel argument\n"
		)
		plugin._cmd.execute = Mock(return_value=(0, help_text, ""))
		self.assertFalse(plugin._rpm_ostree_has_source_flag())

	def test_has_source_flag_in_stderr(self):
		"""--source flag is detected even if it appears in stderr."""
		plugin = self._make_plugin_mock()
		plugin._cmd.execute = Mock(return_value=(0, "", "--source=NAME  Track kargs"))
		self.assertTrue(plugin._rpm_ostree_has_source_flag())

	def test_has_source_flag_help_fails(self):
		"""If rpm-ostree kargs --help fails, --source is not detected."""
		plugin = self._make_plugin_mock()
		plugin._cmd.execute = Mock(return_value=(1, "", "command not found"))
		self.assertFalse(plugin._rpm_ostree_has_source_flag())

	# ------------------------------------------------------------------
	# _rpm_ostree_source_update()
	# ------------------------------------------------------------------

	def test_source_update_basic(self):
		"""--source=tuned is called with correct --append flags."""
		plugin = self._make_plugin_mock()
		plugin._cmdline_val = "nohz=full isolcpus=1-3"
		plugin._cmd.execute = Mock(return_value=(0, "", ""))

		plugin._rpm_ostree_source_update()

		plugin._cmd.execute.assert_called_once_with(
			["rpm-ostree", "kargs", "--source=tuned",
			 "--append=nohz=full", "--append=isolcpus=1-3"],
			return_err=True)
		# Verify bootcmdline state file is updated
		plugin._cmd.add_modify_option_in_file.assert_called_once_with(
			consts.BOOT_CMDLINE_FILE,
			{consts.BOOT_CMDLINE_TUNED_VAR: "nohz=full isolcpus=1-3"})

	def test_source_update_empty_cmdline(self):
		"""When cmdline is empty, only --source=tuned is passed (clears kargs)."""
		plugin = self._make_plugin_mock()
		plugin._cmdline_val = ""
		plugin._cmd.execute = Mock(return_value=(0, "", ""))

		plugin._rpm_ostree_source_update()

		plugin._cmd.execute.assert_called_once_with(
			["rpm-ostree", "kargs", "--source=tuned"],
			return_err=True)
		plugin._cmd.add_modify_option_in_file.assert_called_once_with(
			consts.BOOT_CMDLINE_FILE,
			{consts.BOOT_CMDLINE_TUNED_VAR: ""})

	def test_source_update_rpm_ostree_busy(self):
		"""When rpm-ostree is busy, source update does not execute."""
		plugin = self._make_plugin_mock(rpm_ostree_idle=False)
		plugin._cmdline_val = "nohz=full"
		plugin._cmd.execute = Mock()

		plugin._rpm_ostree_source_update()

		plugin._cmd.execute.assert_not_called()
		plugin._cmd.add_modify_option_in_file.assert_not_called()

	def test_source_update_command_fails(self):
		"""When rpm-ostree kargs --source fails, bootcmdline is not updated."""
		plugin = self._make_plugin_mock()
		plugin._cmdline_val = "nohz=full"
		plugin._cmd.execute = Mock(return_value=(1, "", "error: unknown option"))

		plugin._rpm_ostree_source_update()

		plugin._cmd.execute.assert_called_once()
		plugin._cmd.add_modify_option_in_file.assert_not_called()

	# ------------------------------------------------------------------
	# _remove_rpm_ostree_source_tuning()
	# ------------------------------------------------------------------

	def test_remove_source_tuning(self):
		"""Removal calls --source=tuned with no --append (clears all)."""
		plugin = self._make_plugin_mock()
		plugin._cmd.execute = Mock(return_value=(0, "", ""))

		plugin._remove_rpm_ostree_source_tuning()

		plugin._cmd.execute.assert_called_once_with(
			["rpm-ostree", "kargs", "--source=tuned"],
			return_err=True)
		plugin._cmd.add_modify_option_in_file.assert_called_once_with(
			consts.BOOT_CMDLINE_FILE,
			{consts.BOOT_CMDLINE_TUNED_VAR: ""})

	def test_remove_source_tuning_rpm_ostree_busy(self):
		"""When rpm-ostree is busy, source removal does not execute."""
		plugin = self._make_plugin_mock(rpm_ostree_idle=False)
		plugin._cmd.execute = Mock()

		plugin._remove_rpm_ostree_source_tuning()

		plugin._cmd.execute.assert_not_called()
		# bootcmdline should not be touched either
		plugin._cmd.add_modify_option_in_file.assert_not_called()

	def test_remove_source_tuning_command_fails(self):
		"""When --source removal fails, bootcmdline is still cleared (best-effort)."""
		plugin = self._make_plugin_mock()
		plugin._cmd.execute = Mock(return_value=(1, "", "error"))

		plugin._remove_rpm_ostree_source_tuning()

		# bootcmdline should still be cleared even on failure
		plugin._cmd.add_modify_option_in_file.assert_called_once_with(
			consts.BOOT_CMDLINE_FILE,
			{consts.BOOT_CMDLINE_TUNED_VAR: ""})

	# ------------------------------------------------------------------
	# _rpm_ostree_update() dispatch
	# ------------------------------------------------------------------

	def test_rpm_ostree_update_dispatches_to_source(self):
		"""When --source is available, _rpm_ostree_update uses the source path."""
		plugin = self._make_plugin_mock(has_source=True)
		plugin._cmdline_val = "nohz=full"
		plugin._cmd.execute = Mock(return_value=(0, "", ""))

		plugin._rpm_ostree_update()

		# Should have called --source=tuned
		plugin._cmd.execute.assert_called_once_with(
			["rpm-ostree", "kargs", "--source=tuned", "--append=nohz=full"],
			return_err=True)

	def test_rpm_ostree_update_fallback_when_no_source(self):
		"""When --source is not available, _rpm_ostree_update uses the legacy path."""
		from tuned.plugins.plugin_bootloader import BootloaderPlugin

		plugin = self._make_plugin_mock(has_source=False)
		plugin._cmdline_val = "nohz=full"

		# Set up legacy path dependencies
		plugin._get_appended_rpm_ostree_kargs = Mock(return_value=["old_karg=1"])
		plugin._get_rpm_ostree_kargs = Mock(return_value="root=UUID=xxx old_karg=1")
		plugin._modify_rpm_ostree_kargs = Mock(return_value=True)

		# Bind _rpm_ostree_update with the real method
		# but we need to also bind _patch_bootcmdline for the legacy path
		plugin._rpm_ostree_update = \
			lambda: BootloaderPlugin._rpm_ostree_update(plugin)

		plugin._rpm_ostree_update()

		# Should NOT have called --source, should use legacy delete/append
		plugin._modify_rpm_ostree_kargs.assert_called_once_with(
			delete_kargs=["old_karg=1"], append_kargs=["nohz=full"])

	# ------------------------------------------------------------------
	# _remove_rpm_ostree_tuning() dispatch
	# ------------------------------------------------------------------

	def test_remove_rpm_ostree_tuning_dispatches_to_source(self):
		"""When --source is available, removal uses the source path."""
		plugin = self._make_plugin_mock(has_source=True)
		plugin._cmd.execute = Mock(return_value=(0, "", ""))

		plugin._remove_rpm_ostree_tuning()

		plugin._cmd.execute.assert_called_once_with(
			["rpm-ostree", "kargs", "--source=tuned"],
			return_err=True)

	def test_remove_rpm_ostree_tuning_fallback_when_no_source(self):
		"""When --source is not available, removal uses the legacy path."""
		from tuned.plugins.plugin_bootloader import BootloaderPlugin

		plugin = self._make_plugin_mock(has_source=False)
		plugin._get_appended_rpm_ostree_kargs = Mock(return_value=["old=1", "old=2"])
		plugin._modify_rpm_ostree_kargs = Mock(return_value=True)

		plugin._remove_rpm_ostree_tuning = \
			lambda: BootloaderPlugin._remove_rpm_ostree_tuning(plugin)

		plugin._remove_rpm_ostree_tuning()

		plugin._modify_rpm_ostree_kargs.assert_called_once_with(
			delete_kargs=["old=1", "old=2"])
		plugin._cmd.add_modify_option_in_file.assert_called_once_with(
			consts.BOOT_CMDLINE_FILE,
			{consts.BOOT_CMDLINE_TUNED_VAR: ""})


if __name__ == '__main__':
	unittest.main()
