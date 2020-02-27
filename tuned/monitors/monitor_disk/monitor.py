from .library import DiskMonitorLibrary
import tuned.logs
import tuned.monitors
from tuned.utils.file import FileHandler
import os

log = tuned.logs.get()

class DiskMonitor(tuned.monitors.Monitor):
	@classmethod
	def _init_class(cls):
		file_handler = FileHandler(log_func=log.debug)
		cls._lib = DiskMonitorLibrary(file_handler)
		super(DiskMonitor, cls)._init_class()

	@classmethod
	def _init_available_devices(cls):
		block_devices = os.listdir("/sys/block")
		available = set(filter(cls._is_device_supported, block_devices))
		cls._available_devices = available

		for d in available:
			cls._load[d] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

	@classmethod
	def _is_device_supported(cls, device):
		return cls._lib.is_device_supported(device)

	@classmethod
	def update(cls):
		for device in cls._updating_devices:
			cls._update_disk(device)

	@classmethod
	def _update_disk(cls, dev):
		cls._load[dev] = cls._lib.get_disk_stats(dev)
