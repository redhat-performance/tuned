import os

class DiskTuning:
	def __init__(self):
		self.devidle = {}

	def __updateIdle__(self, dev, devload):
		for type in ("READ", "WRITE"):
			if devload[type] == 0.0:
				idle = self.devidle.setdefault(dev, {})
				idle.setdefault(type, 0)
				idle[type] += 1
			else:
				idle = self.devidle.setdefault(dev, {})
				idle.setdefault(type, 0)
				idle[type] = 0

	def setTuning(self, load):
		disks = load.setdefault("DISK", {})
		for dev in disks.keys():
			devload = disks[dev]
			self.__updateIdle__(dev, devload)
			if self.devidle[dev]["READ"] == 30 and self.devidle[dev]["WRITE"] == 30:
				os.system("hdparm -S5 /dev/"+dev)
    				os.system("hdparm -B1 /dev/"+dev)
		print(load, self.devidle)

_plugin = DiskTuning()
