#!/usr/bin/python3 -Es
import sys
import os
import dbus
import signal
from dbus.mainloop.glib import DBusGMainLoop
from tuned import exports
from tuned.ppd import controller
import tuned.consts as consts


def handle_signal(signal_number, handler):
    def handler_wrapper(_signal_number, _frame):
        if signal_number == _signal_number:
            handler()
    signal.signal(signal_number, handler_wrapper)

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Superuser permissions are required to run the daemon.", file=sys.stderr)
        sys.exit(1)

    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    try:
        tuned_object = bus.get_object(consts.DBUS_BUS, consts.DBUS_OBJECT)
    except dbus.exceptions.DBusException:
        print("TuneD not found on the DBus, ensure that it is running.", file=sys.stderr)
        sys.exit(1)
    tuned_iface = dbus.Interface(tuned_object, consts.DBUS_INTERFACE)

    controller = controller.Controller(bus, tuned_iface)

    handle_signal(signal.SIGINT, controller.terminate)
    handle_signal(signal.SIGTERM, controller.terminate)
    handle_signal(signal.SIGHUP, controller.load_config)

    dbus_exporter = exports.dbus_with_properties.DBusExporterWithProperties(
        consts.PPD_DBUS_BUS, consts.PPD_DBUS_INTERFACE, consts.PPD_DBUS_OBJECT, consts.PPD_NAMESPACE
    )

    exports.register_exporter(dbus_exporter)
    exports.register_object(controller)
    controller.run()
