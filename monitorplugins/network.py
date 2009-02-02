import os

class DiskMonitor:
	def __init__(self):
		self.devices = {}
		dnames = os.listdir("/sys/block/")
		for d in dnames:
			try:
				v = open("/sys/block/"+d+"/device/vendor").read().strip()
			except:
				v = None
			if v != "ATA" and v != "SCSI":
				continue
			self.devices[d] = {}
			self.devices[d]["new"] = ['0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0']
			self.devices[d]["max"] = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
			self.__updateStat__(d)
			self.devices[d]["max"] = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
		print self.devices


	def __calcdiff__(self, dev):
		l = []
		for i in xrange(len(self.devices[dev]["old"])):
			l.append(int(self.devices[dev]["new"][i]) - int(self.devices[dev]["old"][i]))
		return l

	def __updateStat__(self, dev):
		l = open("/sys/block/"+dev+"/stat", "r").read()
		self.devices[dev]["old"] = self.devices[dev]["new"]
		self.devices[dev]["new"] = l.split()
		l = self.__calcdiff__(dev)
		for i in xrange(len(l)):
			if l[i] > self.devices[dev]["max"][i]:
				self.devices[dev]["max"][i] = l[i]

	def __update__(self):
		for dev in self.devices.keys():
			self.__updateStat__(dev)
			self.devices[dev]["diff"] = self.__calcdiff__(dev)
		
	def getLoad(self):
		self.__update__()
		ret = {}
		ret["DISK"] = {}
		for dev in self.devices.keys():
			ret["DISK"][dev] = {}
			ret["DISK"][dev]["READ"] = float(self.devices[dev]["diff"][1]) / float(self.devices[dev]["max"][1])
			ret["DISK"][dev]["WRITE"] = float(self.devices[dev]["diff"][5]) / float(self.devices[dev]["max"][5])
		return ret

_plugin = DiskMonitor()
