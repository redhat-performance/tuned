#!/usr/bin/python3 -Es
import sys
import os
import dbus
import signal
import argparse
import logging
from dbus.mainloop.glib import DBusGMainLoop
from tuned import exports, logs
from tuned.ppd import controller
import tuned.consts as consts


def handle_signal(signal_number, handler):
    def handler_wrapper(_signal_number, _frame):
        if signal_number == _signal_number:
            handler()
    signal.signal(signal_number, handler_wrapper)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PPD compatibility daemon.")
    parser.add_argument("--debug", "-D", action="store_true", help="log debugging messages")
    parser.add_argument(
        "--log",
        "-l",
        nargs="?",
        const=consts.PPD_LOG_FILE,
        help="log to a file, default is " + consts.PPD_LOG_FILE,
    )
    args = parser.parse_args()

    log = logs.get()

    if args.debug:
        log.setLevel(logging.DEBUG)

    if args.log:
        log.switch_to_file(args.log)

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
    handle_signal(signal.SIGHUP, controller.initialize)

    dbus_exporter = exports.dbus_with_properties.DBusExporterWithProperties(
        consts.PPD_DBUS_BUS, consts.PPD_DBUS_INTERFACE, consts.PPD_DBUS_OBJECT, consts.PPD_NAMESPACE
    )

    exports.register_exporter(dbus_exporter)
    exports.register_object(controller)
    controller.run()
