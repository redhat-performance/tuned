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
import re
import logging, tuned_logging
from tuned_nettool import ethcard

log = logging.getLogger("tuned.netmonitor")

class NetMonitor:

	config_section = "NetMonitor"

	def __init__(self):
		self.devices = {}
		self.enabled = True
		tunable = self._tunable_devices()
		for dev in tunable:
			max_speed = self._calcspeed(ethcard(dev).get_max_speed())
			self.devices[dev] = {}
			self.devices[dev]["new"] = ['0', '0', '0', '0']
			self.devices[dev]["max"] = [max_speed, 1, max_speed, 1]
			self._updateStat(dev)
			self.devices[dev]["max"] = [max_speed, 1, max_speed, 1]

	def _tunable_devices(self):
		devices = os.listdir("/sys/class/net")
		tunable = filter(self._device_is_tunable, devices)
		return tunable

	def _device_is_tunable(self, name):
		if self._device_type(name) in ["virtual", "unknown"]:
			return False

		card = ethcard(name)
		return len(card.supported_modes) > 1 and card.get_max_speed() >= 1000

	def _device_type(self, name):
		try:
			path = os.path.join("/sys/class/net", name)
			path = os.path.join(os.path.dirname(path), os.readlink(path))
			path = os.path.normpath(path)
			devtype = re.match(r"/sys/devices/([^/]+)/", path).group(1)
		except (IOError, AttributeError, OSError):
			devtype = "unknown"
			log.info("Cannot determine type of '%s'." % name)

		log.debug("Found network device: %s (%s)" % (name, devtype))
		return devtype

	def _calcspeed(self, speed):
		# 0.6 is just a magical constant (empirical value): Typical workload on netcard won't exceed
		# that and if it does, then the code is smart enough to adapt it.
		# 1024 * 1024 as for MB -> B
		# speed / 8  Mb -> MB
		return (int) (0.6 * 1024 * 1024 * speed / 8)

	def _calcdiff(self, dev):
		l = []
		for i in xrange(len(self.devices[dev]["old"])):
			l.append(int(self.devices[dev]["new"][i]) - int(self.devices[dev]["old"][i]))
		return l

	def _updateStat(self, dev):
		self.devices[dev]["old"] = self.devices[dev]["new"][:]
		l = open("/sys/class/net/"+dev+"/statistics/rx_bytes", "r").read().strip()
		self.devices[dev]["new"][0] = l
		l = open("/sys/class/net/"+dev+"/statistics/rx_packets", "r").read().strip()
		self.devices[dev]["new"][1] = l
		l = open("/sys/class/net/"+dev+"/statistics/tx_bytes", "r").read().strip()
		self.devices[dev]["new"][2] = l
		l = open("/sys/class/net/"+dev+"/statistics/tx_packets", "r").read().strip()
		self.devices[dev]["new"][3] = l
		l = self._calcdiff(dev)
		for i in xrange(len(l)):
			if l[i] > self.devices[dev]["max"][i]:
				self.devices[dev]["max"][i] = l[i]

	def _update(self):
		for dev in self.devices.keys():
			self._updateStat(dev)
			self.devices[dev]["diff"] = self._calcdiff(dev)

			log.debug("%s diff: %s" % (dev, self.devices[dev]["diff"]))

	def init(self, config):
		log.debug("Init")

		self.config = config
		if self.config.has_option(self.config_section, "enabled"):
			self.enabled = (self.config.get(self.config_section, "enabled") == "True")
		interval = self.config.getint("main", "interval")

		log.info("Module is %s" % ("enabled" if self.enabled else "disabled"))

		for d in self.devices.keys():
			max_data = self._calcspeed(ethcard(d).get_max_speed()) * interval;
			self.devices[d]["max"] = [max_data, 1, max_data, 1]

		log.info("Tunable ethernet cards: %s" % ", ".join(self.devices.keys()))

	def cleanup(self):
		log.debug("Cleanup")

	def getLoad(self):
		if not self.enabled:
			return
		self._update()
		ret = {}
		ret["NET"] = {}
		for dev in self.devices.keys():
			ret["NET"][dev] = {}
			ret["NET"][dev]["READ"] = float(self.devices[dev]["diff"][0]) / float(self.devices[dev]["max"][0])
			ret["NET"][dev]["WRITE"] = float(self.devices[dev]["diff"][2]) / float(self.devices[dev]["max"][2])

		return ret

_plugin = NetMonitor()
