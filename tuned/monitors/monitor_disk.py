import tuned.monitors.interface

import os

class DiskMonitor(tuned.monitors.interface.MonitorInterface):

	_supported_vendors = ["ATA", "SCSI"]

	@classmethod
	def _init_available_devices(cls):
		block_devices = os.listdir("/sys/block")
		available = set(filter(cls._is_device_supported, block_devices))
		cls._available_devices = available

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
			# TODO
			cls._load[device] = None

	@classmethod
	def _update_disk(cls, name):
		pass
