import tuned.plugins
import tuned.log
from tuned.utils.commands import *

log = tuned.log.get()

class RFKillPlugin(tuned.plugins.Plugin):
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

	@command_set("disable", per_device=True)
	def _set_disabled(self, value, device):
		log.warn("RF killing is not implemented, ticket #25")

	@command_get("disable")
	def _get_disabled(self, device):
		return False
