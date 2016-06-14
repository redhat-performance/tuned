import dbus
import tuned.logs

log = tuned.logs.get()

class polkit():
	def __init__(self):
		self._bus = dbus.SystemBus()
		self._proxy = self._bus.get_object('org.freedesktop.PolicyKit1', '/org/freedesktop/PolicyKit1/Authority', follow_name_owner_changes = True)
		self._authority = dbus.Interface(self._proxy, dbus_interface='org.freedesktop.PolicyKit1.Authority')

	def check_authorization(self, sender, action_id):
		"""Check authorization, return codes:
			1  - authorized
			2  - polkit error, but authorized with fallback method
			0  - unauthorized
			-1 - polkit error and unauthorized by the fallback method
			-2 - polkit error and unable to use the fallback method
		"""

		if sender is None or action_id is None:
			return False
		details = {}
		flags = 1            # AllowUserInteraction flag
		cancellation_id = "" # No cancellation id
		subject = ("system-bus-name", {"name" : sender})
		try:
			ret = self._authority.CheckAuthorization(subject, action_id, details, flags, cancellation_id)[0]
		except (dbus.exceptions.DBusException, ValueError) as e:
			log.error("error querying polkit: %s" % e)
			# No polkit or polkit error, fallback to always allow root
			try:
				uid = self._bus.get_unix_user(sender)
			except dbus.exceptions.DBusException as e:
				log.error("error using falback authorization method: %s" % e)
				return -2
			if uid == 0:
				return 2
			else:
				return -1
		return 1 if ret else 0
