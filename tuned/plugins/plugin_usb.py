import tuned.plugins
import tuned.log

class USBPlugin(tuned.plugins.Plugin):
	"""
	"""

	def __init__(self, devices, options):
		super(self.__class__, self).__init__(devices, options)

		self.register_command("enable_usb_autosupend",
								self._set_enable_usb_autosupend,
								self._revert_enable_usb_autosupend)

	@classmethod
	def _get_default_options(cls):
		return {
			"enable_usb_autosuspend": None,
		}

	def update_tuning(self):
		# FIXME: can we drop this method?
		pass

	@command("usb", "enable_usb_autosupend")
	def _set_enable_usb_autosupend(self, value):
		old_value = {}
		if value == "1" or value == "true":
			value = "1"
		elif value == "0" or value == "false":
			value = "0"
		else:
			log.warn("Incorrect enable_usb_autosuspend value.")
			return
		for sys_file in glob.glob("/sys/bus/usb/devices/*/power/autosuspend"):
			old_value[sys_file] = tuned.utils.commands.read_file(sys_file)
			tuned.utils.commands.write_to_file(sys_file, value)

		return old_value

	@command_revert("usb", "enable_usb_autosupend")
	def _revert_enable_usb_autosupend(self, values):
		for sys_file, value in values.iteritems():
			tuned.utils.commands.write_to_file(sys_file, value)
