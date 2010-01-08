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

import os
import logging, tuned_logging

log = logging.getLogger("tuned.diskmonitor")

class DiskMonitor:

	config_section = "DiskMonitor"

	def __init__(self):
		self.devices = {}
		self.enabled = True

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

			log.debug("%s diff: %s" % (dev, self.devices[dev]["diff"]))

	def init(self, config):
		log.debug("Init")

		self.config = config
		if self.config.has_option(self.config_section, "enabled"):
			self.enabled = (self.config.get(self.config_section, "enabled") == "True")

		log.info("Module is %s" % ("enabled" if self.enabled else "disabled"))

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

		log.info("Available hard drives: %s" % ", ".join(self.devices.keys()))

	def cleanup(self):
		log.debug("Cleanup")

	def getLoad(self):
		if not self.enabled:
			return
		self.__update__()
		ret = {}
		ret["DISK"] = {}
		for dev in self.devices.keys():
			ret["DISK"][dev] = {}
			ret["DISK"][dev]["READ"] = float(self.devices[dev]["diff"][1]) / float(self.devices[dev]["max"][1])
			ret["DISK"][dev]["WRITE"] = float(self.devices[dev]["diff"][5]) / float(self.devices[dev]["max"][5])
		return ret

_plugin = DiskMonitor()
