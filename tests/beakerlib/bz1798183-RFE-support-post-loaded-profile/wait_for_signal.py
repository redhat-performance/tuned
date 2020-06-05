from dbus.mainloop.glib import DBusGMainLoop
import dbus
from gi.repository import GLib

def handler(profiles, res, err):
    print(profiles)
    loop.quit()

DBusGMainLoop(set_as_default=True)
loop = GLib.MainLoop()
bus=dbus.SystemBus()
bus.add_signal_receiver(handler, "profile_changed", "com.redhat.tuned.control", "com.redhat.tuned", "/Tuned")
loop.run()
