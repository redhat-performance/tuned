import os
import exports
import exports.dbus

DBUS_BUS = "com.redhat.tuned"
DBUS_INTERFACE = "com.redhat.tuned.control"
DBUS_OBJECT = "/Tuned"

class Controller(exports.interfaces.IExportable):
	def __init__(self):
		super(self.__class__, self).__init__()

	@exports.export("", "s")
	def start(self):
		print "== inner start called =="
		return "started (%s)" % self

	@exports.export("", "b")
	def stop(self):
		return False

	@exports.export("", "b")
	def reload(self):
		return False

	@exports.export("s", "b")
	def switch_profile(self, profile):
		return False

	@exports.export("", "s")
	def active_profile(self):
		return "default"

	@exports.export("", "a{bb}")
	def status(self):
		return [ False, False ]

controller = Controller()
dbus_exporter = exports.dbus.DBusExporter(DBUS_BUS, DBUS_INTERFACE, DBUS_OBJECT)

exports.register_exporter(dbus_exporter)
exports.register_object(controller)

exports.run()
