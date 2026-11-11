"""Harmless processes for testing service restart and dependency policy."""
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time

import dbus
import dbus.service

role, directory, name = sys.argv[1:]
directory = Path(directory)
stop = threading.Event()
signal.signal(signal.SIGTERM, lambda *args: stop.set())
signal.signal(signal.SIGINT, lambda *args: stop.set())
bus = None
bus_name = None
if role == "core":
    bus = dbus.SessionBus(private=True)
    bus_name = dbus.service.BusName(name, bus)
with (directory / (role + ".jsonl")).open("a") as f:
    f.write(json.dumps({"pid": os.getpid(), "time": time.monotonic(),
                       "profile": (directory / "selected").read_text().strip()}) + "\n")
exit_code = 0
while not stop.wait(0.05):
    if role == "core":
        once = directory / "fail-once"
        if once.exists() or (directory / "fail-always").exists():
            once.unlink(missing_ok=True)
            exit_code = 1
            break
        if (directory / "exit-cleanly").exists():
            break
# Model Type=dbus shutdown: TuneD closes its exporters before returning the
# failure to its entry point. Losing the name may also deliver SIGTERM.
if bus is not None:
    del bus_name
    bus.close()
    time.sleep(0.05)
sys.exit(exit_code)
