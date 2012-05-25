import base
from decorators import *
import tuned.logs

log = tuned.logs.get()

class RFKillPlugin(base.Plugin):
	"""
	Base class for plugins which can be enabled/disabled using rfkill.
	"""

	#
	# TODO: ticket #25
	#

	@classmethod
	def _get_default_options(cls):
		return {
			"disable" : None,
		}

	def _rfkill_device_type(self):
		raise NotImplementedError()

	def _rfkill_devices(self):
		# rfkill list <self._rfkill_device_type()>
		return []

	@command_set("disable", per_device=True)
	def _set_disabled(self, value, device):
		log.warn("RF killing is not implemented, ticket #25")

	@command_get("disable")
	def _get_disabled(self, device):
		return False
