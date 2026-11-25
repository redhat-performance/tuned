import errno
import unittest

try:
	from unittest.mock import Mock
except ImportError:
	from mock import Mock


class CPUPluginBoostTestCase(unittest.TestCase):
	"""Tests for the global/per-policy boost interaction in the cpu plugin.

	Some drivers/platforms gate per-policy boost control behind the
	package-wide global toggle: the per-policy node can reject writes
	with EINVAL until the global node is enabled first (e.g. amd-pstate
	in active/EPP mode, or some ARM/Snapdragon laptops, see #810). These
	tests exercise writing the global node before the per-policy one,
	and the read-side fallback, without instantiating the full
	CPULatencyPlugin (which requires a real hardware inventory).
	"""

	def _make_plugin_mock(self, has_intel_pstate=False):
		"""Build a Mock exposing the real boost-related methods under test.

		Avoids instantiating the full CPULatencyPlugin, which requires a
		real hardware inventory; only the attributes/methods the boost
		code path touches are wired up.
		"""
		from tuned.plugins.plugin_cpu import CPULatencyPlugin

		plugin = Mock(spec=CPULatencyPlugin)
		plugin._has_intel_pstate = has_intel_pstate
		plugin._cmd = Mock()
		plugin._cmd.get_bool = lambda v: str(v)
		plugin._is_cpu_online = Mock(return_value=True)

		plugin._pstate_boost_path = \
			lambda cpu_id: CPULatencyPlugin._pstate_boost_path(plugin, cpu_id)
		plugin._global_boost_path = \
			lambda: CPULatencyPlugin._global_boost_path(plugin)
		plugin._set_boost = \
			lambda boost, device, instance, sim, remove: \
				CPULatencyPlugin._set_boost(plugin, boost, device, instance, sim, remove)
		plugin._get_boost = \
			lambda device, instance, ignore_missing=False: \
				CPULatencyPlugin._get_boost(plugin, device, instance, ignore_missing)

		return plugin

	def test_set_boost_writes_global_before_per_policy(self):
		"""Both writes succeed; global must be attempted before per-policy."""
		plugin = self._make_plugin_mock()

		import os
		orig_exists = os.path.exists
		os.path.exists = lambda p: True
		try:
			plugin._cmd.write_to_file = Mock(return_value=True)
			result = plugin._set_boost("1", "cpu0", None, sim=False, remove=False)
		finally:
			os.path.exists = orig_exists

		self.assertEqual(result, "1")
		paths_written = [c.args[0] for c in plugin._cmd.write_to_file.call_args_list]
		self.assertEqual(paths_written, [
			plugin._global_boost_path(),
			plugin._pstate_boost_path("0"),
		])

	def test_set_boost_per_policy_still_attempted_after_global_succeeds(self):
		"""Global write succeeds; per-policy write is still attempted, not skipped."""
		plugin = self._make_plugin_mock()

		import os
		orig_exists = os.path.exists
		os.path.exists = lambda p: True
		try:
			def write_to_file(path, data, no_error=False, ignore_same=False):
				"""Simulate a driver where the global write succeeds but per-policy still EINVALs."""
				if path == plugin._global_boost_path():
					return True
				if path == plugin._pstate_boost_path("0"):
					return False  # simulates a driver where per-policy still EINVALs
				raise AssertionError("unexpected path: %s" % path)
			plugin._cmd.write_to_file = Mock(side_effect=write_to_file)

			result = plugin._set_boost("1", "cpu0", None, sim=False, remove=False)
		finally:
			os.path.exists = orig_exists

		# global write alone is enough to report success
		self.assertEqual(result, "1")
		per_policy_calls = [c for c in plugin._cmd.write_to_file.call_args_list
			if c.args[0] == plugin._pstate_boost_path("0")]
		self.assertEqual(len(per_policy_calls), 1)

	def test_set_boost_succeeds_via_per_policy_when_global_node_missing(self):
		"""No global boost node at all; per-policy write alone is still tried."""
		plugin = self._make_plugin_mock()

		import os
		orig_exists = os.path.exists
		os.path.exists = lambda p: p == plugin._pstate_boost_path("0")
		try:
			plugin._cmd.write_to_file = Mock(return_value=True)
			result = plugin._set_boost("1", "cpu0", None, sim=False, remove=False)
		finally:
			os.path.exists = orig_exists

		self.assertEqual(result, "1")
		self.assertEqual(plugin._cmd.write_to_file.call_count, 1)
		self.assertEqual(
			plugin._cmd.write_to_file.call_args.args[0],
			plugin._pstate_boost_path("0"))

	def test_set_boost_no_fallback_when_global_node_missing(self):
		"""Neither per-policy nor global boost paths exist; no write attempted, no crash."""
		plugin = self._make_plugin_mock()

		import os
		orig_exists = os.path.exists
		os.path.exists = lambda p: False
		try:
			plugin._cmd.write_to_file = Mock(return_value=True)
			result = plugin._set_boost("1", "cpu0", None, sim=False, remove=False)
		finally:
			os.path.exists = orig_exists

		self.assertIsNone(result)
		plugin._cmd.write_to_file.assert_not_called()

	def test_get_boost_falls_back_to_global_node_when_per_policy_fails(self):
		"""Per-policy write-verify fails; value should come from the global node."""
		plugin = self._make_plugin_mock()

		import os
		orig_exists = os.path.exists
		os.path.exists = lambda p: True
		try:
			plugin._cmd.read_file = Mock(side_effect=lambda p: {
				plugin._pstate_boost_path("0"): "0",
				plugin._global_boost_path(): "1",
			}[p])
			plugin._cmd.write_to_file = Mock(return_value=False)

			result = plugin._get_boost("cpu0", None)
		finally:
			os.path.exists = orig_exists

		self.assertEqual(result, "1")


if __name__ == "__main__":
	unittest.main()
