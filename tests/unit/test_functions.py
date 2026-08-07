import os
import shutil
import subprocess
import tempfile
import unittest


class WifiPowerSaveTestCase(unittest.TestCase):
	def setUp(self):
		self._repo_dir = os.path.abspath(
			os.path.join(os.path.dirname(__file__), "..", "..")
		)
		self._test_dir = tempfile.mkdtemp()
		self._bin_dir = os.path.join(self._test_dir, "bin")
		os.mkdir(self._bin_dir)
		self._log = os.path.join(self._test_dir, "commands.log")
		self._wireless = os.path.join(self._test_dir, "wireless")
		self._write_file(
			self._wireless,
			"""\
Inter-| sta-|   Quality        |   Discarded packets               | Missed | WE
 face | tus | link level noise |  nwid  crypt   frag  retry   misc | beacon | 22
wlan0: 0000    0.    0.    0.       0      0      0      0      0        0
wlan1: 0000    0.    0.    0.       0      0      0      0      0        0
"""
		)
		for command in ("grep", "ls", "sed"):
			os.symlink("/bin/" + command, os.path.join(self._bin_dir, command))

	def tearDown(self):
		shutil.rmtree(self._test_dir)

	def _write_file(self, path, content):
		with open(path, "w") as output:
			output.write(content)

	def _write_command(self, name, body):
		command = os.path.join(self._bin_dir, name)
		self._write_file(command, "#!/bin/bash\n" + body.lstrip())
		os.chmod(command, 0o755)

	def _run(self, level):
		env = os.environ.copy()
		env["COMMAND_LOG"] = self._log
		env["PATH"] = self._bin_dir
		subprocess.check_call(
			[
				"/bin/bash",
				"-c",
				'. "$1"; _wifi_set_power_level "$2" "$3"',
				"bash",
				os.path.join(self._repo_dir, "functions"),
				str(level),
				self._wireless,
			],
			env=env,
		)
		if os.path.exists(self._log):
			with open(self._log) as command_log:
				return command_log.read().splitlines()
		return []

	def test_iw_enables_power_save_on_all_interfaces(self):
		self._write_command("iw", 'echo "iw $*" >> "$COMMAND_LOG"\n')
		self._write_command("iwpriv", 'echo "iwpriv $*" >> "$COMMAND_LOG"\n')

		self.assertEqual(
			self._run(5),
			[
				"iw dev wlan0 set power_save on",
				"iw dev wlan1 set power_save on",
			],
		)

	def test_iw_disables_power_save_on_all_interfaces(self):
		self._write_command("iw", 'echo "iw $*" >> "$COMMAND_LOG"\n')

		self.assertEqual(
			self._run(0),
			[
				"iw dev wlan0 set power_save off",
				"iw dev wlan1 set power_save off",
			],
		)

	def test_iw_maps_legacy_disable_level_to_off(self):
		self._write_command("iw", 'echo "iw $*" >> "$COMMAND_LOG"\n')

		self.assertEqual(
			self._run(6),
			[
				"iw dev wlan0 set power_save off",
				"iw dev wlan1 set power_save off",
			],
		)

	def test_iwpriv_fallback_when_iw_is_unavailable(self):
		self._write_command("iwpriv", 'echo "iwpriv $*" >> "$COMMAND_LOG"\n')

		self.assertEqual(
			self._run(5),
			[
				"iwpriv wlan0 set_power 5",
				"iwpriv wlan1 set_power 5",
			],
		)

	def test_iwpriv_fallback_when_iw_rejects_interface(self):
		self._write_command(
			"iw",
			"""
echo "iw $*" >> "$COMMAND_LOG"
exit 1
""",
		)
		self._write_command("iwpriv", 'echo "iwpriv $*" >> "$COMMAND_LOG"\n')

		self.assertEqual(
			self._run(5),
			[
				"iw dev wlan0 set power_save on",
				"iwpriv wlan0 set_power 5",
				"iw dev wlan1 set power_save on",
				"iwpriv wlan1 set_power 5",
			],
		)

	def test_missing_tools_are_ignored(self):
		self.assertEqual(self._run(5), [])

	def test_no_interfaces_are_ignored(self):
		self._write_file(
			self._wireless,
			"""\
Inter-| sta-|   Quality        |   Discarded packets               | Missed | WE
 face | tus | link level noise |  nwid  crypt   frag  retry   misc | beacon | 22
"""
		)
		self._write_command("iw", 'echo "iw $*" >> "$COMMAND_LOG"\n')

		self.assertEqual(self._run(5), [])


if __name__ == "__main__":
	unittest.main()
