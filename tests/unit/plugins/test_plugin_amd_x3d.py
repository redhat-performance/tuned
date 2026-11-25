import tempfile
import unittest

try:
	from unittest.mock import Mock
	from unittest.mock import call
	from unittest.mock import patch
except ImportError:
	from mock import Mock
	from mock import call
	from mock import patch

from tuned.monitors.repository import Repository
from tuned.plugins.plugin_amd_x3d import AMDX3DPlugin
from tuned.plugins.plugin_amd_x3d import _find_x3d_paths
from tuned.utils.commands import commands
import tuned.plugins as plugins
import tuned.profiles as profiles
from tuned import storage


class AMDX3DPluginTestCase(unittest.TestCase):
	def setUp(self):
		self._storage_file = tempfile.NamedTemporaryFile()
		plugin_instance_factory = plugins.instance.Factory()
		storage_provider = storage.PickleProvider(self._storage_file.name)
		storage_factory = storage.Factory(storage_provider)

		self._plugin = AMDX3DPlugin(
			Repository(),
			storage_factory,
			Mock(),
			Mock(),
			Mock(),
			plugin_instance_factory,
			None,
			profiles.variables.Variables(),
		)
		self._plugin._cmd = commands()
		self._plugin._cmd.read_file = Mock()
		self._plugin._cmd.write_to_file = Mock()

	def tearDown(self):
		self._storage_file.close()

	def _create_instance(self, mode="cache"):
		instance = self._plugin.create_instance(
			"amd_x3d",
			0,
			"",
			None,
			"",
			"",
			{"mode": mode},
		)
		self._plugin.initialize_instance(instance)
		return instance

	def test_find_x3d_paths_sorted(self):
		with patch("tuned.plugins.plugin_amd_x3d.glob.glob",
				return_value=["/sys/devices/b", "/sys/devices/a"]):
			self.assertEqual(_find_x3d_paths(),
				["/sys/devices/a", "/sys/devices/b"])

	def test_apply_verify_and_unapply_mode(self):
		paths = [
			"/sys/bus/platform/drivers/amd_x3d_vcache/AMDI0001:00/amd_x3d_mode",
			"/sys/bus/platform/drivers/amd_x3d_vcache/AMDI0002:00/amd_x3d_mode",
		]
		instance = self._create_instance(mode="cache")

		with patch.object(self._plugin, "_x3d_paths", return_value=paths):
			self._plugin._cmd.read_file.return_value = "frequency\n"
			instance.apply_tuning()

			self.assertEqual(
				self._plugin._storage_get(instance, self._plugin._commands["mode"]),
				"frequency",
			)
			self._plugin._cmd.write_to_file.assert_has_calls([
				call(paths[0], "cache", no_error=False),
				call(paths[1], "cache", no_error=False),
			])

			self._plugin._cmd.read_file.reset_mock()
			self._plugin._cmd.write_to_file.reset_mock()
			self._plugin._cmd.read_file.return_value = "frequency [cache]\n"
			self.assertTrue(instance.verify_tuning(False))
			self._plugin._cmd.write_to_file.assert_not_called()

			self._plugin._cmd.read_file.reset_mock()
			self._plugin._cmd.write_to_file.reset_mock()
			instance.unapply_tuning()

			self._plugin._cmd.write_to_file.assert_has_calls([
				call(paths[0], "frequency", no_error=False),
				call(paths[1], "frequency", no_error=False),
			])
			self.assertIsNone(
				self._plugin._storage_get(instance, self._plugin._commands["mode"])
			)

	def test_apply_without_supported_device_is_noop(self):
		instance = self._create_instance(mode="cache")

		with patch.object(self._plugin, "_x3d_paths", return_value=[]):
			instance.apply_tuning()

		self._plugin._cmd.write_to_file.assert_not_called()
		self.assertIsNone(
			self._plugin._storage_get(instance, self._plugin._commands["mode"])
		)
