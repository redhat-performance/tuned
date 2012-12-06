import pyudev
import re

__all__ = ["Enumerator"]

class Enumerator(object):
	"""
	Class for system devices enumeration.
	"""

	def __init__(self):
		self._context = pyudev.Context()

	def _device_fulfills_requirements(self, device, requirements):
		for attribute, requirement in requirements.items():

			if hasattr(device, attribute):
				value = getattr(device, attribute)

				if requirement is None:
					pass
				elif isinstance(requirement, str):
					if value != requirement:
						return False
				elif isinstance(requirement, re._pattern_type):
					if requirement.match(value) is None:
						return False
				else:
					raise TypeError("Invalid type of a requirement for a device.")

			else:
				# custom callbacks with non-existing attributes
				if callable(requirement):
					if not requirement(device):
						return False
				else:
					return False

		else:
			return True

	def get_devices(self, **requirements):
		subsystem = requirements.get("subsystem", None)
		if subsystem is not None:
			del requirements["subsystem"]

		devices = self._context.list_devices(subsystem = subsystem)
		return [dev for dev in devices if self._device_fulfills_requirements(dev, requirements)]
