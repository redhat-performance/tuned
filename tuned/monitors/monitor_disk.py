import tuned.monitors
import os

class DiskMonitor(tuned.monitors.Monitor):

	_supported_vendors = ["ATA", "SCSI"]

	@classmethod
	def _init_available_devices(cls):
		block_devices = os.listdir("/sys/block")
		available = set(filter(cls._is_device_supported, block_devices))
		cls._available_devices = available

		for d in available:
			cls._load[d] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

	@classmethod
	def _is_device_supported(cls, device):
		vendor_file = "/sys/block/%s/device/vendor" % device
		try:
			vendor = open(vendor_file).read().strip()
		except IOError:
			return False

		return vendor in cls._supported_vendors

	@classmethod
	def update(cls):
		for device in cls._updating_devices:
			cls._update_disk(device)

	@classmethod
	def _update_disk(cls, dev):
		with open("/sys/block/" + dev + "/stat") as statfile:
			cls._load[dev] = list(map(int, statfile.read().split()))
