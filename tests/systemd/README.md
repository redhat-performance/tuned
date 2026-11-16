# Automatic recovery integration tests

Run these opt-in tests as an ordinary user in a session with a working
`systemd --user` manager, session D-Bus, and Python `dbus` bindings:

```sh
python3 tests/systemd/test_recovery.py
```

They create uniquely named, transient user services and remove them on exit.
They neither start the installed TuneD/PPD services nor change hardware tuning.
The core fixture owns a private session-bus name to exercise `Type=dbus`,
including releasing the name before returning a failure. The bridge fixture
exercises `Requires`, `After` and `PartOf`. Restart delay and start limits are
read from the proposed `tuned.service`.

Four checks verify failure recovery of both active services, an intentional
stop, a clean process exit, and exhaustion of the three-start limit. The
fixtures log their process IDs and read a temporary selected-profile file.
These checks exercise systemd's service policy; actual TuneD and PPD profile
persistence and reloading are tested separately by the unit tests in
`tests/unit/daemon/test_restart_profile.py` and
`tests/unit/ppd/test_restart_profile.py`.

The tests take approximately 40 seconds because they use the actual five-second
restart delay. No polling is added to the production services. Profile holds
owned by applications are transient and are not reconstructed across a PPD
process restart; the saved user-selected base profile is restored.
