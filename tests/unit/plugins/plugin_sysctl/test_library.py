import errno
import unittest

from tests.unit.lib import create_IOError, create_OSError
from tests.unit.lib import MockFileOperations, MockLogger
from tuned.plugins.plugin_sysctl.library import SysctlLib
from tuned.utils.file import FileHandler

class SysctlLibTestCase(unittest.TestCase):
	def test_get_sysctl_path(self):
		lib = SysctlLib(None, None, None)
		option = "net.netfilter.nf_conntrack_max"
		expected = "/proc/sys/net/netfilter/nf_conntrack_max"
		self.assertEqual(lib._get_sysctl_path(option), expected)

		option = "vm.swappiness"
		expected = "/proc/sys/vm/swappiness"
		self.assertEqual(lib._get_sysctl_path(option), expected)

	def test_read_sysctl(self):
		file_ops = MockFileOperations()
		file_ops.files["/proc/sys/net/ipv4/icmp_echo_ignore_all"] = "0\n"
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()
		lib = SysctlLib(file_handler, None, logger)
		option = "net.ipv4.icmp_echo_ignore_all"

		res = lib.read_sysctl(option)

		self.assertEqual(res, "0")
		self.assertEqual(len(logger.msgs), 1)
		self.assertEqual(logger.msgs[0][0], "debug")
		self.assertIn("Value of sysctl parameter", logger.msgs[0][1])
		self.assertIn(option, logger.msgs[0][1])
		self.assertIn("'0'", logger.msgs[0][1])

	def test_read_sysctl_multiline(self):
		file_ops = MockFileOperations()
		file_ops.files["/proc/sys/dev/cdrom/info"] = "CD-ROM information, Id: cdrom.c 3.20 2003/12/17\n\ndrive name:	\n"
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()
		lib = SysctlLib(file_handler, None, logger)
		option = "dev.cdrom.info"

		res = lib.read_sysctl(option)

		self.assertIsNone(res)
		self.assertEqual(len(logger.msgs), 1)
		self.assertEqual(logger.msgs[0][0], "error")
		self.assertIn("Failed to read sysctl parameter", logger.msgs[0][1])
		self.assertIn(option, logger.msgs[0][1])
		self.assertIn("multi-line", logger.msgs[0][1])

	def test_read_sysctl_nonexistent(self):
		file_ops = MockFileOperations()
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()
		lib = SysctlLib(file_handler, None, logger)
		option = "foo.bar"

		res = lib.read_sysctl(option)

		self.assertIsNone(res)
		self.assertEqual(len(logger.msgs), 1)
		self.assertEqual(logger.msgs[0][0], "error")
		self.assertIn("Failed to read sysctl parameter", logger.msgs[0][1])
		self.assertIn(option, logger.msgs[0][1])
		self.assertIn("does not exist", logger.msgs[0][1])

	def test_read_sysctl_inaccessible(self):
		file_ops = MockFileOperations(error_to_raise=errno.EACCES)
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()
		lib = SysctlLib(file_handler, None, logger)
		option = "vm.swappiness"

		res = lib.read_sysctl(option)

		self.assertIsNone(res)
		self.assertEqual(len(logger.msgs), 1)
		self.assertEqual(logger.msgs[0][0], "error")
		self.assertIn("Failed to read sysctl parameter", logger.msgs[0][1])
		self.assertIn(option, logger.msgs[0][1])
		self.assertIn("Permission denied", logger.msgs[0][1])

	def test_write_sysctl(self):
		file_ops = MockFileOperations()
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()
		lib = SysctlLib(file_handler, None, logger)
		option = "vm.swappiness"

		res = lib.write_sysctl(option, "30")

		self.assertTrue(res)
		self.assertEqual(len(logger.msgs), 1)
		self.assertEqual(logger.msgs[0][0], "debug")
		self.assertIn("Setting sysctl parameter", logger.msgs[0][1])
		self.assertIn(option, logger.msgs[0][1])
		self.assertIn("30", logger.msgs[0][1])

	def test_write_sysctl_base_reachable_time_deprecated(self):
		file_ops = MockFileOperations()
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()
		lib = SysctlLib(file_handler, None, logger)
		option = "base_reachable_time"

		res = lib.write_sysctl(option, "5")

		self.assertFalse(res)
		self.assertEqual(len(logger.msgs), 1)
		self.assertEqual(logger.msgs[0][0], "error")
		self.assertIn("Refusing to set deprecated sysctl", logger.msgs[0][1])
		self.assertIn(option, logger.msgs[0][1])

	def test_write_sysctl_retrans_time_deprecated(self):
		file_ops = MockFileOperations()
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()
		lib = SysctlLib(file_handler, None, logger)
		option = "retrans_time"

		res = lib.write_sysctl(option, "7")

		self.assertFalse(res)
		self.assertEqual(len(logger.msgs), 1)
		self.assertEqual(logger.msgs[0][0], "error")
		self.assertIn("Refusing to set deprecated sysctl", logger.msgs[0][1])
		self.assertIn(option, logger.msgs[0][1])

	def test_write_sysctl_nonexistent(self):
		file_ops = MockFileOperations(error_to_raise=errno.ENOENT)
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()
		lib = SysctlLib(file_handler, None, logger)
		option = "foo.bar"

		res = lib.write_sysctl(option, "foobar")

		self.assertFalse(res)
		self.assertEqual(len(logger.msgs), 2)

		self.assertEqual(logger.msgs[0][0], "debug")
		self.assertIn("Setting sysctl parameter", logger.msgs[0][1])
		self.assertIn(option, logger.msgs[0][1])
		self.assertIn("foobar", logger.msgs[0][1])

		self.assertEqual(logger.msgs[1][0], "error")
		self.assertIn("Failed to set sysctl", logger.msgs[1][1])
		self.assertIn(option, logger.msgs[1][1])
		self.assertIn("does not exist", logger.msgs[1][1])

	def test_write_sysctl_inaccessible(self):
		file_ops = MockFileOperations(error_to_raise=errno.EACCES)
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()
		lib = SysctlLib(file_handler, None, logger)
		option = "vm.swappiness"

		res = lib.write_sysctl(option, "10")

		self.assertFalse(res)
		self.assertEqual(len(logger.msgs), 2)

		self.assertEqual(logger.msgs[0][0], "debug")
		self.assertIn("Setting sysctl parameter", logger.msgs[0][1])
		self.assertIn(option, logger.msgs[0][1])
		self.assertIn("10", logger.msgs[0][1])

		self.assertEqual(logger.msgs[1][0], "error")
		self.assertIn("Failed to set sysctl", logger.msgs[1][1])
		self.assertIn(option, logger.msgs[1][1])
		self.assertIn("Permission denied", logger.msgs[1][1])

	def test_write_sysctl_ignore_missing(self):
		file_ops = MockFileOperations(error_to_raise=errno.ENOENT)
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()
		lib = SysctlLib(file_handler, None, logger)
		option = "net.bridge.bridge-nf-call-arptables"

		res = lib.write_sysctl(option, "0", ignore_missing=True)

		self.assertFalse(res)
		self.assertEqual(len(logger.msgs), 2)

		self.assertEqual(logger.msgs[0][0], "debug")
		self.assertIn("Setting sysctl parameter", logger.msgs[0][1])
		self.assertIn(option, logger.msgs[0][1])
		self.assertIn("0", logger.msgs[0][1])

		self.assertEqual(logger.msgs[1][0], "debug")
		self.assertIn("Failed to set sysctl", logger.msgs[1][1])
		self.assertIn(option, logger.msgs[1][1])
		self.assertIn("does not exist", logger.msgs[1][1])

	def test_apply_system_sysctl_run_sysctl_d(self):
		file_ops = MockFileOperations()
		file_ops.files["/run/sysctl.d/30-bar.conf"] = "vm.swappiness = 20\n"
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()

		def listdir(path):
			if path == "/run/sysctl.d":
				return ["30-bar.conf"]
			else:
				raise create_OSError(errno.ENOENT, path)

		lib = SysctlLib(file_handler, listdir, logger)

		lib.apply_system_sysctl()

		self.assertEqual(len(file_ops.files), 2)
		self.assertEqual(file_ops.files["/proc/sys/vm/swappiness"],
				 "20")
		self.assertEqual(logger.msgs[0][0], "debug")
		self.assertEqual(logger.msgs[0][1],
				 "Applying sysctl settings from file /run/sysctl.d/30-bar.conf")
		self.assertEqual(logger.msgs[1][0], "debug")
		self.assertEqual(logger.msgs[1][1],
				 "Setting sysctl parameter 'vm.swappiness' to '20'")
		self.assertEqual(logger.msgs[2][0], "debug")
		self.assertEqual(logger.msgs[2][1],
				 "Finished applying sysctl settings from file /run/sysctl.d/30-bar.conf")

	def test_apply_system_sysctl_etc_sysctl_d(self):
		file_ops = MockFileOperations()
		file_ops.files["/etc/sysctl.d/50-foo.conf"] = "vm.swappiness = 50\n"
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()

		def listdir(path):
			if path == "/etc/sysctl.d":
				return ["50-foo.conf"]
			else:
				raise create_OSError(errno.ENOENT, path)

		lib = SysctlLib(file_handler, listdir, logger)

		lib.apply_system_sysctl()

		self.assertEqual(len(file_ops.files), 2)
		self.assertEqual(file_ops.files["/proc/sys/vm/swappiness"],
				 "50")

	def test_apply_system_sysctl_etc_sysctl_conf(self):
		file_ops = MockFileOperations()
		file_ops.files["/etc/sysctl.conf"] = "vm.swappiness = 10\n"
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()

		def listdir(path):
			raise create_OSError(errno.ENOENT, path)

		lib = SysctlLib(file_handler, listdir, logger)

		lib.apply_system_sysctl()

		self.assertEqual(len(file_ops.files), 2)
		self.assertEqual(file_ops.files["/proc/sys/vm/swappiness"],
				 "10")

	def test_apply_system_sysctl_precedence(self):
		file_ops = MockFileOperations()
		file_ops.files["/run/sysctl.d/50-foo.conf"] = "vm.swappiness = 20\n"
		file_ops.files["/etc/sysctl.d/50-foo.conf"] = "net.ipv4.icmp_echo_ignore_all = 1\n"
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()

		def listdir(path):
			if path in ["/run/sysctl.d", "/etc/sysctl.d"]:
				return ["50-foo.conf"]
			else:
				raise create_OSError(errno.ENOENT, path)

		lib = SysctlLib(file_handler, listdir, logger)

		lib.apply_system_sysctl()

		# Only one of the 50-foo.conf files (namely the one in
		# /run/sysctl.d) and the sysctl.conf file should get read
		self.assertEqual(file_ops.read_called, 2)
		# Two 50-foo.conf files, plus swappiness
		self.assertEqual(len(file_ops.files), 3)
		self.assertEqual(file_ops.files["/proc/sys/vm/swappiness"],
				 "20")

	def test_apply_system_sysctl_sysctl_conf_overrides(self):
		file_ops = MockFileOperations()
		file_ops.files["/run/sysctl.d/50-foo.conf"] = \
			"vm.swappiness = 20\nnet.ipv4.icmp_echo_ignore_all = 1\n"
		file_ops.files["/etc/sysctl.conf"] = \
			"vm.swappiness = 10\n"
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()

		def listdir(path):
			if path == "/run/sysctl.d":
				return ["50-foo.conf"]
			else:
				raise create_OSError(errno.ENOENT, path)

		lib = SysctlLib(file_handler, listdir, logger)

		lib.apply_system_sysctl()

		# 50-foo.conf and sysctl.conf should get read
		self.assertEqual(file_ops.read_called, 2)
		# 50-foo.conf, sysctl.conf, icmp_echo_ignore_all and swappiness
		self.assertEqual(len(file_ops.files), 4)
		self.assertEqual(file_ops.files["/proc/sys/vm/swappiness"],
				 "10")
		self.assertEqual(file_ops.files["/proc/sys/net/ipv4/icmp_echo_ignore_all"],
				 "1")

	def test_apply_system_sysctl_nonexistent(self):
		file_ops = MockFileOperations()
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()

		def listdir(path):
			raise create_OSError(errno.ENOENT, path)

		lib = SysctlLib(file_handler, listdir, logger)

		lib.apply_system_sysctl()

		self.assertEqual(len(file_ops.files), 0)
		self.assertEqual(file_ops.read_called, 1)
		self.assertEqual(file_ops.write_called, 0)

	def test_apply_system_sysctl_non_conf_files_ignored(self):
		file_ops = MockFileOperations()
		file_ops.files["/etc/sysctl.d/foo"] = "vm.swappiness = 10\n"
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()

		def listdir(path):
			if path == "/etc/sysctl.d":
				return ["foo"]
			else:
				raise create_OSError(errno.ENOENT, path)

		lib = SysctlLib(file_handler, listdir, logger)

		lib.apply_system_sysctl()

		self.assertEqual(len(file_ops.files), 1)
		self.assertEqual(file_ops.read_called, 1)
		self.assertEqual(file_ops.write_called, 0)

	def test_apply_system_sysctl_inaccessible(self):
		file_ops = MockFileOperations(error_to_raise=errno.EACCES)
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()

		def listdir(path):
			raise create_OSError(errno.EACCES, path)

		lib = SysctlLib(file_handler, listdir, logger)

		lib.apply_system_sysctl()

		self.assertEqual(len(file_ops.files), 0)
		self.assertEqual(file_ops.read_called, 1)
		self.assertEqual(file_ops.write_called, 0)
		self.assertEqual(len(logger.msgs), 2)
		self.assertEqual(logger.msgs[0][0], "debug")
		self.assertEqual(logger.msgs[0][1], "Applying sysctl settings from file /etc/sysctl.conf")
		self.assertEqual(logger.msgs[1][0], "error")
		self.assertIn("Error reading sysctl settings from file /etc/sysctl.conf",
			      logger.msgs[1][1])
		self.assertIn("Permission denied", logger.msgs[1][1])

	def test_apply_system_sysctl_syntax_error_1(self):
		file_ops = MockFileOperations()
		file_ops.files["/etc/sysctl.conf"] = "vm.swappiness\n"
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()

		def listdir(path):
			raise create_OSError(errno.ENOENT, path)

		lib = SysctlLib(file_handler, listdir, logger)

		lib.apply_system_sysctl()

		self.assertEqual(len(file_ops.files), 1)
		self.assertEqual(file_ops.read_called, 1)
		self.assertEqual(file_ops.write_called, 0)
		self.assertEqual(len(logger.msgs), 3)
		self.assertEqual(logger.msgs[0][0], "debug")
		self.assertEqual(logger.msgs[0][1], "Applying sysctl settings from file /etc/sysctl.conf")
		self.assertEqual(logger.msgs[1][0], "error")
		self.assertEqual(logger.msgs[1][1], "Syntax error in file /etc/sysctl.conf, line 1")
		self.assertEqual(logger.msgs[2][0], "debug")
		self.assertEqual(logger.msgs[2][1], "Finished applying sysctl settings from file /etc/sysctl.conf")

	def test_apply_system_sysctl_syntax_error_2(self):
		file_ops = MockFileOperations()
		file_ops.files["/etc/sysctl.conf"] = "=10\n"
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()

		def listdir(path):
			raise create_OSError(errno.ENOENT, path)

		lib = SysctlLib(file_handler, listdir, logger)

		lib.apply_system_sysctl()

		self.assertEqual(len(file_ops.files), 1)
		self.assertEqual(file_ops.read_called, 1)
		self.assertEqual(file_ops.write_called, 0)
		self.assertEqual(len(logger.msgs), 3)
		self.assertEqual(logger.msgs[0][0], "debug")
		self.assertEqual(logger.msgs[0][1], "Applying sysctl settings from file /etc/sysctl.conf")
		self.assertEqual(logger.msgs[1][0], "error")
		self.assertEqual(logger.msgs[1][1], "Syntax error in file /etc/sysctl.conf, line 1")
		self.assertEqual(logger.msgs[2][0], "debug")
		self.assertEqual(logger.msgs[2][1], "Finished applying sysctl settings from file /etc/sysctl.conf")

	def test_apply_system_sysctl_ignore_missing(self):
		class MyFileOps(MockFileOperations):
			def write(self, path, contents):
				self.write_called += 1
				raise create_IOError(errno.ENOENT, path)

		file_ops = MyFileOps()
		option = "net.bridge.bridge-nf-call-arptables"
		file_ops.files["/etc/sysctl.conf"] =  option + " = 0\n"
		file_handler = FileHandler(file_ops=file_ops)
		logger = MockLogger()

		def listdir(path):
			raise create_OSError(errno.ENOENT, path)

		lib = SysctlLib(file_handler, listdir, logger)

		lib.apply_system_sysctl()

		self.assertGreater(len(logger.msgs), 0)
		for log_level, msg in logger.msgs:
			self.assertNotEqual(log_level, "error")
		self.assertIn(("debug",
			       "Failed to set sysctl parameter '%s' to '0', the parameter does not exist" % option),
			      logger.msgs)
