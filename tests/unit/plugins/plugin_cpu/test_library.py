import errno
import unittest

from tests.unit.lib import MockFileOperations, MockLogger
from tuned.plugins.plugin_cpu.library import CPULatencyLibrary
from tuned.utils.file import FileHandler

class CPULatencyLibraryTestCase(unittest.TestCase):
	def test_get_intel_pstate_attr(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		file_ops.files["/sys/devices/system/cpu/intel_pstate/min_perf_pct"] = "9\n"
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPULatencyLibrary(file_handler, logger)

		res = lib.get_intel_pstate_attr("min_perf_pct")

		self.assertEqual(res, "9")
		self.assertEqual(file_ops.read_called, 1)
		self.assertEqual(file_ops.write_called, 0)
		self.assertEqual(len(logger.msgs), 0)

	def test_get_intel_pstate_attr_nonexistent(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPULatencyLibrary(file_handler, logger)

		res = lib.get_intel_pstate_attr("no_turbo")

		self.assertIsNone(res)
		self.assertEqual(file_ops.read_called, 1)
		self.assertEqual(file_ops.write_called, 0)
		self.assertEqual(len(logger.msgs), 1)
		self.assertEqual(logger.msgs[0][0], "error")
		self.assertIn("Failed to get intel_pstate attribute",
			      logger.msgs[0][1])
		self.assertIn("no_turbo",
			      logger.msgs[0][1])
		self.assertIn("No such file",
			      logger.msgs[0][1])

	def test_get_intel_pstate_attr_inaccessible(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		file_ops.error_to_raise = errno.EACCES
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPULatencyLibrary(file_handler, logger)

		res = lib.get_intel_pstate_attr("max_perf_pct")

		self.assertIsNone(res)
		self.assertEqual(file_ops.read_called, 1)
		self.assertEqual(file_ops.write_called, 0)
		self.assertEqual(len(logger.msgs), 1)
		self.assertEqual(logger.msgs[0][0], "error")
		self.assertIn("Failed to get intel_pstate attribute",
			      logger.msgs[0][1])
		self.assertIn("max_perf_pct",
			      logger.msgs[0][1])
		self.assertIn("Permission denied",
			      logger.msgs[0][1])

	def test_set_intel_pstate_attr(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPULatencyLibrary(file_handler, logger)

		lib.set_intel_pstate_attr("min_perf_pct", "8")

		self.assertEqual(file_ops.files["/sys/devices/system/cpu/intel_pstate/min_perf_pct"], "8")
		self.assertEqual(file_ops.read_called, 0)
		self.assertEqual(file_ops.write_called, 1)
		self.assertEqual(len(logger.msgs), 0)

	def test_set_intel_pstate_attr_None_val(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPULatencyLibrary(file_handler, logger)

		lib.set_intel_pstate_attr("min_perf_pct", None)

		self.assertEqual(len(file_ops.files), 0)
		self.assertEqual(file_ops.read_called, 0)
		self.assertEqual(file_ops.write_called, 0)
		self.assertEqual(len(logger.msgs), 0)

	def test_set_intel_pstate_attr_inaccessible(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		file_ops.error_to_raise = errno.EACCES
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPULatencyLibrary(file_handler, logger)

		lib.set_intel_pstate_attr("max_perf_pct", "7")

		self.assertEqual(file_ops.read_called, 0)
		self.assertEqual(file_ops.write_called, 1)
		self.assertEqual(len(logger.msgs), 1)
		self.assertEqual(logger.msgs[0][0], "error")
		self.assertIn("Failed to set intel_pstate attribute",
			      logger.msgs[0][1])
		self.assertIn("max_perf_pct",
			      logger.msgs[0][1])
		self.assertIn("Permission denied",
			      logger.msgs[0][1])

	def test_get_available_governors(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		file_ops.files["/sys/devices/system/cpu/cpu3/cpufreq/scaling_available_governors"] = "performance powersave\n"
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPULatencyLibrary(file_handler, logger)

		res = lib.get_available_governors("cpu3")

		self.assertEqual(res, ["performance", "powersave"])
		self.assertEqual(file_ops.read_called, 1)
		self.assertEqual(file_ops.write_called, 0)
		self.assertEqual(len(logger.msgs), 0)

	def test_get_available_governors_nonexistent(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		file_ops.files["/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors"] = "performance powersave\n"
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPULatencyLibrary(file_handler, logger)

		res = lib.get_available_governors("cpu2")

		self.assertEqual(res, [])
		self.assertEqual(file_ops.read_called, 1)
		self.assertEqual(file_ops.write_called, 0)
		self.assertEqual(len(logger.msgs), 1)
		self.assertEqual(logger.msgs[0][0], "error")
		self.assertIn("Failed to read scaling governors",
			      logger.msgs[0][1])
		self.assertIn("cpu2", logger.msgs[0][1])
		self.assertIn("No such file", logger.msgs[0][1])

	def test_get_governor_on_cpu(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		file_ops.files["/sys/devices/system/cpu/cpu1/cpufreq/scaling_governor"] = "powersave\n"
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPULatencyLibrary(file_handler, logger)

		res = lib.get_governor_on_cpu("cpu1", False)

		self.assertEqual(res, "powersave")
		self.assertEqual(file_ops.read_called, 1)
		self.assertEqual(file_ops.write_called, 0)
		self.assertEqual(len(logger.msgs), 0)

	def test_get_governor_on_cpu_nonexistent(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		file_ops.files["/sys/devices/system/cpu/cpu1/cpufreq/scaling_governor"] = "powersave\n"
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPULatencyLibrary(file_handler, logger)

		res = lib.get_governor_on_cpu("cpu2", False)

		self.assertEqual(res, "")
		self.assertEqual(file_ops.read_called, 1)
		self.assertEqual(file_ops.write_called, 0)
		self.assertEqual(len(logger.msgs), 1)
		self.assertEqual(logger.msgs[0][0], "error")
		self.assertIn("Failed to read scaling governor", logger.msgs[0][1])
		self.assertIn("cpu2", logger.msgs[0][1])
		self.assertIn("No such file", logger.msgs[0][1])

	def test_get_governor_on_cpu_no_error(self):
		logger = MockLogger()
		file_ops = MockFileOperations(error_to_raise=errno.EACCES)
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPULatencyLibrary(file_handler, logger)

		res = lib.get_governor_on_cpu("cpu2", True)

		self.assertEqual(res, "")
		self.assertEqual(file_ops.read_called, 1)
		self.assertEqual(file_ops.write_called, 0)
		for log_level, msg in logger.msgs:
			self.assertNotEqual(log_level, "error")

	def test_set_governor_on_cpu(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPULatencyLibrary(file_handler, logger)

		lib.set_governor_on_cpu("performance", "cpu1")

		self.assertEqual(file_ops.read_called, 0)
		self.assertEqual(file_ops.write_called, 1)
		self.assertEqual(file_ops.files["/sys/devices/system/cpu/cpu1/cpufreq/scaling_governor"],
				 "performance")
		self.assertEqual(len(logger.msgs), 1)
		self.assertEqual(logger.msgs[0][0], "info")
		self.assertEqual(logger.msgs[0][1],
				 "setting governor 'performance' on cpu 'cpu1'")

	def test_set_governor_on_cpu_nonexistent(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		file_ops.error_to_raise = errno.ENOENT
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPULatencyLibrary(file_handler, logger)

		lib.set_governor_on_cpu("performance", "cpu2")

		self.assertEqual(file_ops.read_called, 0)
		self.assertEqual(file_ops.write_called, 1)
		self.assertEqual(len(logger.msgs), 2)
		self.assertEqual(logger.msgs[0][0], "info")
		self.assertEqual(logger.msgs[0][1],
				 "setting governor 'performance' on cpu 'cpu2'")
		self.assertEqual(logger.msgs[1][0], "error")
		self.assertIn("Failed to set scaling governor", logger.msgs[1][1])
		self.assertIn("performance", logger.msgs[1][1])
		self.assertIn("cpu2", logger.msgs[1][1])
		self.assertIn("No such file", logger.msgs[1][1])

	def test_sampling_down_factor_path(self):
		lib = CPULatencyLibrary(None, None)
		res = lib.sampling_down_factor_path()
		self.assertEqual(res,
				 "/sys/devices/system/cpu/cpufreq/ondemand/sampling_down_factor")

		res = lib.sampling_down_factor_path("powersave")
		self.assertEqual(res,
				 "/sys/devices/system/cpu/cpufreq/powersave/sampling_down_factor")

	def test_get_sampling_down_factor(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPULatencyLibrary(file_handler, logger)
		path = lib.sampling_down_factor_path("ondemand")
		file_ops.files[path] = "1\n"

		res = lib.get_sampling_down_factor(path, "ondemand")

		self.assertEqual(res, "1")
		self.assertEqual(file_ops.read_called, 1)
		self.assertEqual(file_ops.write_called, 0)
		self.assertEqual(len(logger.msgs), 0)

	def test_get_sampling_down_factor_nonexistent(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPULatencyLibrary(file_handler, logger)
		path = lib.sampling_down_factor_path("powersave")

		res = lib.get_sampling_down_factor(path, "powersave")

		self.assertEqual(res, "")
		self.assertEqual(file_ops.read_called, 1)
		self.assertEqual(file_ops.write_called, 0)
		self.assertEqual(len(logger.msgs), 1)
		self.assertEqual(logger.msgs[0][0], "error")
		self.assertIn("Failed to get sampling_down_factor", logger.msgs[0][1])
		self.assertIn("powersave", logger.msgs[0][1])
		self.assertIn("No such file", logger.msgs[0][1])

	def test_set_sampling_down_factor(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPULatencyLibrary(file_handler, logger)
		path = lib.sampling_down_factor_path("ondemand")

		lib.set_sampling_down_factor(path, "100", "ondemand")

		self.assertEqual(file_ops.read_called, 0)
		self.assertEqual(file_ops.write_called, 1)
		self.assertEqual(len(logger.msgs), 1)
		self.assertEqual(logger.msgs[0][0], "info")
		self.assertIn("setting sampling_down_factor", logger.msgs[0][1])
		self.assertIn("100", logger.msgs[0][1])
		self.assertIn("ondemand", logger.msgs[0][1])

	def test_set_sampling_down_factor_nonexistent(self):
		logger = MockLogger()
		file_ops = MockFileOperations()
		file_ops.error_to_raise = errno.ENOENT
		file_handler = FileHandler(file_ops=file_ops)
		lib = CPULatencyLibrary(file_handler, logger)
		path = lib.sampling_down_factor_path("powersave")

		lib.set_sampling_down_factor(path, "1", "powersave")

		self.assertEqual(file_ops.read_called, 0)
		self.assertEqual(file_ops.write_called, 1)
		self.assertEqual(len(logger.msgs), 2)
		self.assertEqual(logger.msgs[0][0], "info")
		self.assertIn("setting sampling_down_factor", logger.msgs[0][1])
		self.assertIn("1", logger.msgs[0][1])
		self.assertIn("powersave", logger.msgs[0][1])
		self.assertEqual(logger.msgs[1][0], "error")
		self.assertIn("Failed to set sampling_down_factor", logger.msgs[1][1])
		self.assertIn("powersave", logger.msgs[1][1])
		self.assertIn("1", logger.msgs[1][1])
		self.assertIn("No such file", logger.msgs[1][1])
