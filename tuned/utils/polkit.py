import dbus

class polkit():
	def __init__(self):
		bus = dbus.SystemBus()
		proxy = bus.get_object('org.freedesktop.PolicyKit1', '/org/freedesktop/PolicyKit1/Authority')
		self._authority = dbus.Interface(proxy, dbus_interface='org.freedesktop.PolicyKit1.Authority')

	def check_authorization(self, sender, action_id):
		if sender is None or action_id is None:
			return False
		details = {}
		flags = 1            # AllowUserInteraction flag
		cancellation_id = '' # No cancellation id
		subject = ('system-bus-name', {'name' : sender})
		return self._authority.CheckAuthorization(subject, action_id, details, flags, cancellation_id)[0]
