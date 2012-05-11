import tuned.plugins
import tuned.logs
import tuned.monitors
from tuned.utils.commands import *
import os
import struct
import glob

log = tuned.logs.get()

class WirelessPlugin(tuned.plugins.RFKillPlugin):
	"""
	Plugin for setting wireless powersaving options.
	"""

	@classmethod
	def _get_default_options(cls):
		return {
			"dynamic_tuning" : "0",
			"power_level"    : None,
		}

	def cleanup(self):
		pass

	def update_tuning(self):
		pass

	@command_set("power_level", per_device=True)
	def _set_power_level(self, value, device):
		# TODO: not implemented ticket #26
		# 1. iwpriv <interface> set_power <power_level>
		# 2. /sys/bus/pci/devices/*/power_level
		log.warn("setting wifi power_level is not implemented, ticket #26")

	@command_get("power_level")
	def _get_power_level(self, device):
		return None
