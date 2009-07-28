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

class CPUTuning:
	def __init__(self):
		self.latency = 100
		self.enabled = True

	def init(self, config):
		self.config = config
		if self.config.has_option("CPUTuning", "enabled"):
                        self.enabled = (self.config.get("CPUTuning", "enabled") == "True")
		try:
			open("/dev/cpu_dma_latency", "w")
		except:
			self.enabled = False

	def cleanup(self):
		if not self.enabled:
			return
		open("/dev/cpu_dma_latency", "w").write("100\n")

	def setTuning(self, load):
		if not self.enabled:
			return
		loadavg = load.setdefault("CPU", 0.0)
		if self.latency == 100 and loadavg < 0.2:
			self.latency = 999
			open("/dev/cpu_dma_latency", "w").write("999\n")
		if self.latency == 999 and loadavg > 0.2:
			self.latency = 100
			open("/dev/cpu_dma_latency", "w").write("100\n")

_plugin = CPUTuning()
