import tuned.monitors.interface

import os

class DiskMonitor(tuned.monitors.interface.MonitorInterface):
	@classmethod
	def _init_available_devices(cls):
		block_devices = os.listdir("/sys/block")
		available = set(filter(cls._is_device_supported, block_devices))
		cls._available_devices = available

	@classmethod
	def _is_device_supported(cls, device):
		capability_name = "/sys/block/%s/capability" % device
		capability = (int) (open(capability_name).read())

		# FIXME: not sure about this
		# !GENHD_FL_REMOVABLE && !GENHD_FL_CD
		return (capability & 9) == 0

	@classmethod
	def update(cls):
		for device in cls._updating_devices:
			# TODO
			cls._load[device] = None
