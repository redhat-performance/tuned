class DiskMonitorLibrary(object):

	_supported_vendors = ["ATA", "SCSI"]

	def __init__(self, file_handler):
		self._file_handler = file_handler

	def is_device_supported(self, device):
		vendor_file = "/sys/block/%s/device/vendor" % device
		try:
			vendor = self._file_handler.read(vendor_file).strip()
		except IOError:
			return False

		return vendor in self._supported_vendors

	def get_disk_stats(self, device):
		path = "/sys/block/" + device + "/stat"
		content = self._file_handler.read(path)
		return list(map(int, content.split()))
