import json
import unittest

try:
	from unittest.mock import Mock
except ImportError:
	from mock import Mock

from tuned.utils.bootc import has_set_options_for_source


class BootcCapabilityTestCase(unittest.TestCase):
	def setUp(self):
		self.cmd = Mock()
		self.help_result = (0, 'Usage: bootc loader-entries...', '')

	def test_missing_command(self):
		for rc in (1, 127, -2):
			self.cmd.execute.reset_mock()
			self.cmd.execute.return_value = (rc, '', 'unavailable')
			self.assertFalse(has_set_options_for_source(self.cmd))
			self.cmd.execute.assert_called_once_with(
				['bootc', 'loader-entries', 'set-options-for-source', '--help'],
				return_err=True)

	def test_booted_deployment(self):
		for booted in [{'ostree': {'stateroot': 'default'}, 'image': None},
				{'composefs': {'verity': 'abc'}, 'ostree': None}]:
			status = {'status': {'booted': booted}}
			self.cmd.execute.side_effect = [self.help_result, (0, json.dumps(status), '')]
			self.assertTrue(has_set_options_for_source(self.cmd))
			self.cmd.execute.assert_called_with(['bootc', 'status', '--json'], return_err=True)

	def test_not_booted(self):
		# A staged or rollback image does not establish how this host booted.
		status = {'status': {'booted': None, 'staged': {'composefs': {'verity': 'abc'}}}}
		self.cmd.execute.side_effect = [self.help_result, (0, json.dumps(status), '')]
		self.assertFalse(has_set_options_for_source(self.cmd))

	def test_status_failure(self):
		self.cmd.execute.side_effect = [self.help_result, (1, '', 'failed to read status')]
		self.assertFalse(has_set_options_for_source(self.cmd))

	def test_invalid_status(self):
		for out in ['', 'invalid json', 'null', '[]', '{}', '{"status": null}',
				'{"status": {}}', '{"status": {"booted": {}}}']:
			self.cmd.execute.side_effect = [self.help_result, (0, out, '')]
			self.assertFalse(has_set_options_for_source(self.cmd), out)
