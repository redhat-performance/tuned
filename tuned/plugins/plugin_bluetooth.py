import rfkill

class BluetoothPlugin(rfkill.RFKillPlugin):
	"""
	Plugin for tuning bluetooth devices.
	"""

	#
	# TODO: ticket #24
	#

	def _post_init(self):
		self._dynamic_tuning = False
