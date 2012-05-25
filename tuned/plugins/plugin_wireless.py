import rfkill
from decorators import *
#import tuned.logs

#log = tuned.logs.get()

class WirelessPlugin(rfkill.RFKillPlugin):
	"""
	Plugin for setting wireless powersaving options.
	"""

	def _post_init(self):
		self._dynamic_tuning = False

	@classmethod
	def _get_default_options(cls):
		return {
			"power_level"    : None,
		}

	@command_set("power_level", per_device=True)
	def _set_power_level(self, value, device):
		# TODO: not implemented ticket #26
		# 1. iwpriv <interface> set_power <power_level>
		# 2. /sys/bus/pci/devices/*/power_level
		log.warn("setting wifi power_level is not implemented, ticket #26")

	@command_get("power_level")
	def _get_power_level(self, device):
		return None
