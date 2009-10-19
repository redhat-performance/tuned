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

class NetMonitor:
	def __init__(self):
		self.devices = {}
		self.enabled = True
		self.verbose = False
		devs = open("/proc/net/dev").readlines()
		for l in devs:
			l = l.replace(":", " ")
			v = l.split()
			d = v[0]
			if not d.startswith("eth"):
				continue
			self.devices[d] = {}
			self.devices[d]["new"] = ['0', '0', '0', '0']
			# Assume 1gbit interfaces for now. FIXME: Need clean way to figure out max interface speed
			self.devices[d]["max"] = [70*1024*1024, 1, 70*1024*1024, 1]
			self.__updateStat__(d)
			self.devices[d]["max"] = [70*1024*1024, 1, 70*1024*1024, 1]

	def __calcdiff__(self, dev):
		l = []
		for i in xrange(len(self.devices[dev]["old"])):
			l.append(int(self.devices[dev]["new"][i]) - int(self.devices[dev]["old"][i]))
		return l

	def __updateStat__(self, dev):
		self.devices[dev]["old"] = self.devices[dev]["new"][:]
		l = open("/sys/class/net/"+dev+"/statistics/rx_bytes", "r").read().strip()
		self.devices[dev]["new"][0] = l
		l = open("/sys/class/net/"+dev+"/statistics/rx_packets", "r").read().strip()
		self.devices[dev]["new"][1] = l
		l = open("/sys/class/net/"+dev+"/statistics/tx_bytes", "r").read().strip()
		self.devices[dev]["new"][2] = l
		l = open("/sys/class/net/"+dev+"/statistics/tx_packets", "r").read().strip()
		self.devices[dev]["new"][3] = l
		l = self.__calcdiff__(dev)
		for i in xrange(len(l)):
			if l[i] > self.devices[dev]["max"][i]:
				self.devices[dev]["max"][i] = l[i]

	def __update__(self):
		for dev in self.devices.keys():
			self.__updateStat__(dev)
			self.devices[dev]["diff"] = self.__calcdiff__(dev)

	def init(self, config):
		self.config = config
		if self.config.has_option("NetMonitor", "enabled"):
                        self.enabled = (self.config.get("NetMonitor", "enabled") == "True")
		interval = self.config.getint("main", "interval")
		try:
			self.verbose = (self.config.get("main", "verbose") == "True")
			self.verbose = (self.config.get("NetMonitor", "verbose") == "True")
		except:
			pass
		# Assume 1gbit interfaces for now. FIXME: Need clean way to figure out max interface speed
		for d in self.devices.keys():
			self.devices[d]["max"] = [70*1024*1024*interval, 1, 70*1024*1024*interval, 1]

		if self.verbose:
			print self.devices

	def cleanup(self):
		pass

	def getLoad(self):
		if not self.enabled:
			return
		self.__update__()
		ret = {}
		ret["NET"] = {}
		for dev in self.devices.keys():
			ret["NET"][dev] = {}
			ret["NET"][dev]["READ"] = float(self.devices[dev]["diff"][0]) / float(self.devices[dev]["max"][0])
			ret["NET"][dev]["WRITE"] = float(self.devices[dev]["diff"][2]) / float(self.devices[dev]["max"][2])
		if self.verbose:
			print self.devices
		return ret

_plugin = NetMonitor()
