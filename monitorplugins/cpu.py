# Copyright (C) 2009 Red Hat, Inc.
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

log = logging.getLogger("tuned.cpumonitor")

class CPUMonitor:
	def __init__(self):
		self.__update__()
		self.enabled = True

	def __update__(self):
		self.loadavg = float(open("/proc/loadavg").read().split()[0])
		log.debug("Load is %s" % self.loadavg)

	def init(self, config):
		log.debug("Init")
		self.config = config
		log.info("Module is %s" % ("enabled" if self.enabled else "disabled"))
		if self.config.has_option("CPUMonitor", "enabled"):
                        self.enabled = (self.config.get("CPUMonitor", "enabled") == "True")

	def cleanup(self):
		log.debug("Cleanup")

	def getLoad(self):
		if not self.enabled:
			return
		self.__update__()
		ret = {}
		ret["CPU"] = self.loadavg
		return ret

_plugin = CPUMonitor()
