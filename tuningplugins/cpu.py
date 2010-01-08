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

log = logging.getLogger("tuned.cputuning")

class CPUTuning:

	config_section = "CPUTuning"

	def __init__(self):
		self.latency = 100
		self.enabled = True

	def init(self, config):
		log.debug("Init")

		self.config = config
		if self.config.has_option(self.config_section, "enabled"):
                        self.enabled = (self.config.get(self.config_section, "enabled") == "True")
		try:
			open("/dev/cpu_dma_latency", "w")
		except:
			self.enabled = False

		log.info("Module is %s" % ("enabled" if self.enabled else "disabled"))

	def cleanup(self):
		log.debug("Cleanup")
		if not self.enabled:
			return
		open("/dev/cpu_dma_latency", "w").write("100\n")

	def setTuning(self, load):
		if not self.enabled:
			return
		loadavg = load.setdefault("CPU", 0.0)
		if self.latency == 100 and loadavg < 0.2:
			log.debug("Setting latency to 999")
			self.latency = 999
			open("/dev/cpu_dma_latency", "w").write("999\n")
		if self.latency == 999 and loadavg > 0.2:
			log.debug("Setting latency to 100")
			self.latency = 100
			open("/dev/cpu_dma_latency", "w").write("100\n")

_plugin = CPUTuning()
