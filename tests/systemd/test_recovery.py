"""Opt-in integration checks using temporary systemd --user services."""
import configparser
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import uuid


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).with_name("recovery_fixture.py")


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="tuned-recovery-test-")
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)
        (self.path / "selected").write_text("performance\n")
        token = "p" + uuid.uuid4().hex
        self.core = "tuned-recovery-test-" + token + ".service"
        self.bridge = "tuned-ppd-recovery-test-" + token + ".service"
        self.bus_name = "org.example.TunedRecoveryTest." + token
        self.addCleanup(self.stop_units)
        self.config = configparser.ConfigParser(interpolation=None, strict=False)
        self.config.read(ROOT / "tuned.service")
        ppd = configparser.ConfigParser(interpolation=None, strict=False)
        ppd.read(ROOT / "tuned/ppd/tuned-ppd.service")
        self.assertIn("tuned.service", ppd["Unit"]["PartOf"].split())

    def command(self, *args, check=True):
        return subprocess.run(args, check=check, text=True, capture_output=True, timeout=15)

    def stop_units(self):
        self.command("systemctl", "--user", "stop", self.bridge, self.core, check=False)
        self.command("systemctl", "--user", "reset-failed", self.bridge, self.core, check=False)

    def start_core(self):
        props = ["Type=dbus", "BusName=" + self.bus_name, "TimeoutStartSec=10s"]
        for section, key in [("Service", "Restart"), ("Service", "RestartSec"),
                             ("Unit", "StartLimitIntervalSec"), ("Unit", "StartLimitBurst")]:
            props.append(key + "=" + self.config[section][key])
        argv = ["systemd-run", "--user", "--quiet", "--unit=" + self.core]
        for prop in props:
            argv.extend(["--property", prop])
        self.command(*argv, sys.executable, str(FIXTURE), "core", str(self.path), self.bus_name)

    def start_bridge(self):
        self.command("systemd-run", "--user", "--quiet", "--unit=" + self.bridge,
                     "--property=Type=exec", "--property=Requires=" + self.core,
                     "--property=After=" + self.core, "--property=PartOf=" + self.core,
                     sys.executable, str(FIXTURE), "bridge", str(self.path), self.bus_name)

    def records(self, role):
        p = self.path / (role + ".jsonl")
        return [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []

    def state(self, unit, prop="ActiveState"):
        return self.command("systemctl", "--user", "show", unit, "-p", prop, "--value").stdout.strip()

    def wait_for(self, predicate, timeout=25):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.1)
        self.fail("Condition not reached; core=%s bridge=%s" %
                  (self.records("core"), self.records("bridge")))

    def test_failure_restarts_core_and_active_bridge(self):
        self.start_core()
        self.start_bridge()
        self.wait_for(lambda: len(self.records("bridge")) == 1)
        failed_at = time.monotonic()
        (self.path / "fail-once").touch()
        self.wait_for(lambda: len(self.records("core")) == 2 and len(self.records("bridge")) == 2)
        self.assertEqual(self.state(self.core), "active")
        self.assertEqual(self.state(self.bridge), "active")
        self.assertGreaterEqual(self.records("core")[1]["time"] - failed_at, 4.9)
        for role in ("core", "bridge"):
            self.assertNotEqual(self.records(role)[0]["pid"], self.records(role)[1]["pid"])
            self.assertEqual([x["profile"] for x in self.records(role)], ["performance"] * 2)

    def test_intentional_stop_is_not_restarted(self):
        self.start_core()
        self.start_bridge()
        self.wait_for(lambda: len(self.records("bridge")) == 1)
        self.command("systemctl", "--user", "stop", self.core)
        time.sleep(6)
        self.assertEqual(len(self.records("core")), 1)
        self.assertEqual(len(self.records("bridge")), 1)
        self.assertNotEqual(self.state(self.core), "active")
        self.assertNotEqual(self.state(self.bridge), "active")

    def test_clean_exit_is_not_restarted(self):
        self.start_core()
        (self.path / "exit-cleanly").touch()
        self.wait_for(lambda: self.state(self.core) != "active")
        time.sleep(6)
        self.assertEqual(len(self.records("core")), 1)

    def test_repeated_failure_hits_start_limit(self):
        self.start_core()
        (self.path / "fail-always").touch()
        # Some systemd versions retain the last process result (exit-code)
        # when the next automatic start is rate-limited.
        self.wait_for(lambda: self.state(self.core) == "failed")
        time.sleep(6)
        self.assertEqual(len(self.records("core")), 3)
        self.assertEqual(self.state(self.core), "failed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
