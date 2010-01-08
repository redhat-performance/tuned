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
import logging, tuned_logging
from tuned_nettool import ethcard

log = logging.getLogger("tuned.nettuning")

class NetTuning:

	config_section = "NetTuning"

	def __init__(self):
		self.devidle = {}
		self.enabled = True

	def __updateIdle__(self, dev, devload):
		idle = self.devidle.setdefault(dev, {})
		idle.setdefault("LEVEL", 0)
		for type in ("READ", "WRITE"):
			if devload[type] <= 0.05:
				idle.setdefault(type, 0)
				idle[type] += 1
			else:
				idle.setdefault(type, 0)
				idle[type] = 0

	def init(self, config):
		log.debug("Init")

		self.config = config
		if self.config.has_option(self.config_section, "enabled"):
			self.enabled = (self.config.get(self.config_section, "enabled") == "True")

		log.info("Module is %s" % ("enabled" if self.enabled else "disabled"))

	def cleanup(self):
		log.debug("Cleanup")

		for dev in self.devidle.keys():
			if self.enabled and self.devidle[dev]["LEVEL"] > 0:
				ethcard(dev).set_max_speed()

	def setTuning(self, load):
		if not self.enabled:
			return
		disks = load.setdefault("NET", {})
		for dev in disks.keys():
			devload = disks[dev]
			self.__updateIdle__(dev, devload)
			if self.devidle[dev]["LEVEL"] == 0 and self.devidle[dev]["READ"] >= 6 and self.devidle[dev]["WRITE"] >= 6:
				self.devidle[dev]["LEVEL"] = 1

				log.debug("%s: setting 100Mbps" % dev)
				ethcard(dev).set_speed(100) # FIXME: what about making this more dynamic?
			if self.devidle[dev]["LEVEL"] > 0 and (self.devidle[dev]["READ"] == 0 or self.devidle[dev]["WRITE"] == 0):
				self.devidle[dev]["LEVEL"] = 0

				log.debug("%s: setting maximal speed" % dev)
				ethcard(dev).set_max_speed()

_plugin = NetTuning()
