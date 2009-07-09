# Copyright (C) 2008, 2009 Red Hat, Inc.
# Authors: Phil Knirsch
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#

import os, copy

class DiskTuning:
	def __init__(self):
		self.devidle = {}
		self.enabled = True
		self.spins = ["0", "250", "240", "230", "220", "210", "200", "190", "180", "170", "160", "150", "140", "130", "120", "110", "100", "90", "80", "70", "60"]
		self.power = ["255", "225", "195", "165", "155", "145", "135", "125", "115", "100", "90", "80", "70", "60"]

	def __updateIdle__(self, dev, devload):
		idle = self.devidle.setdefault(dev, {})
		idle.setdefault("LEVEL", 0)
		for type in ("READ", "WRITE"):
			if devload[type] == 0.0:
				idle.setdefault(type, 0)
				idle[type] += 1
			else:
				idle.setdefault(type, 0)
				idle[type] = 0

	def init(self, config):
		self.config = config
		if self.config.has_option("DiskTuning", "enabled"):
                        self.enabled = (self.config.get("DiskTuning", "enabled") == "True")

	def cleanup(self):
		for dev in self.devidle.keys():
			if self.enabled and self.devidle[dev]["LEVEL"] > 0:
				os.system("hdparm -S0 -B255 /dev/"+dev+" > /dev/null 2>&1")

	def setTuning(self, load):
		if not self.enabled:
			return
		disks = load.setdefault("DISK", {})
		for dev in disks.keys():
			devload = disks[dev]
			self.__updateIdle__(dev, devload)
			if self.devidle[dev]["LEVEL"] == 0 and self.devidle[dev]["READ"] >= 30 and self.devidle[dev]["WRITE"] >= 30:
				self.devidle[dev]["LEVEL"] = 1
				os.system("hdparm -Y -S60 -B1 /dev/"+dev+" > /dev/null 2>&1")
			if self.devidle[dev]["LEVEL"] > 0 and (self.devidle[dev]["READ"] == 0 or self.devidle[dev]["WRITE"] == 0):
				self.devidle[dev]["LEVEL"] = 0
				os.system("hdparm -S255 -B127 /dev/"+dev+" > /dev/null 2>&1")
		print(load, self.devidle)

_plugin = DiskTuning()
