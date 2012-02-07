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
			cls._load[d] = {}
			cls._load[d]["new"] = ['0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0']
			cls._load[d]["max"] = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
			cls._update_disk(d)
			cls._load[d]["max"] = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

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
		l = open("/sys/block/"+dev+"/stat", "r").read()
		cls._load[dev]["old"] = cls._load[dev]["new"]
		cls._load[dev]["new"] = l.split()
		l = cls._calcdiff(dev)
		for i in xrange(len(l)):
			if l[i] > cls._load[dev]["max"][i]:
				cls._load[dev]["max"][i] = l[i]

		cls._load[dev]['diff'] = cls._calcdiff(dev)
		cls._load[dev]["READ"] = float(cls._load[dev]["diff"][1]) / float(cls._load[dev]["max"][1])
		cls._load[dev]["WRITE"] = float(cls._load[dev]["diff"][5]) / float(cls._load[dev]["max"][5])

	@classmethod
	def _calcdiff(cls, dev):
		l = []
		for i in xrange(len(cls._load[dev]["old"])):
			l.append(int(cls._load[dev]["new"][i]) - int(cls._load[dev]["old"][i]))
		return l
