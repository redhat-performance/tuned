from tuned import exports, logs
from tuned.utils.commands import commands
from tuned.consts import PPD_CONFIG_FILE
from tuned.ppd.config import PPDConfig, PPD_PERFORMANCE, PPD_POWER_SAVER
from enum import StrEnum
import threading
import dbus
import os

log = logs.get()

DRIVER = "tuned"
NO_TURBO_PATH = "/sys/devices/system/cpu/intel_pstate/no_turbo"
LAP_MODE_PATH = "/sys/bus/platform/devices/thinkpad_acpi/dytc_lapmode"

UPOWER_DBUS_NAME = "org.freedesktop.UPower"
UPOWER_DBUS_PATH = "/org/freedesktop/UPower"
UPOWER_DBUS_INTERFACE = "org.freedesktop.UPower"

class PerformanceDegraded(StrEnum):
    NONE = ""
    LAP_DETECTED = "lap-detected"
    HIGH_OPERATING_TEMPERATURE = "high-operating-temperature"


class ProfileHold(object):
    def __init__(self, profile, reason, app_id, watch):
        self.profile = profile
        self.reason = reason
        self.app_id = app_id
        self.watch = watch

    def as_dict(self):
        return {
            "Profile": self.profile,
            "Reason": self.reason,
            "ApplicationId": self.app_id,
        }


class ProfileHoldManager(object):
    def __init__(self, controller):
        self._holds = {}
        self._cookie_counter = 0
        self._controller = controller

    def _callback(self, cookie, app_id):
        def callback(name):
            if name == "":
                log.info("Application '%s' disappeared, releasing hold '%s'" % (app_id, cookie))
                self.remove(cookie)

        return callback

    def _effective_hold_profile(self):
        if any(hold.profile == PPD_POWER_SAVER for hold in self._holds.values()):
            return PPD_POWER_SAVER
        return PPD_PERFORMANCE

    def _cancel(self, cookie):
        if cookie not in self._holds:
            return
        hold = self._holds.pop(cookie)
        hold.watch.cancel()
        exports.send_signal("ProfileReleased", cookie)
        exports.property_changed("ActiveProfileHolds", self.as_dbus_array())
        log.info("Releasing hold '%s': profile '%s' by application '%s'" % (cookie, hold.profile, hold.app_id))

    def as_dbus_array(self):
        return dbus.Array([hold.as_dict() for hold in self._holds.values()], signature="a{sv}")

    def add(self, profile, reason, app_id, caller):
        cookie = self._cookie_counter
        self._cookie_counter += 1
        watch = self._controller.bus.watch_name_owner(caller, self._callback(cookie, app_id))
        log.info("Adding hold '%s': profile '%s' by application '%s'" % (cookie, profile, app_id))
        self._holds[cookie] = ProfileHold(profile, reason, app_id, watch)
        exports.property_changed("ActiveProfileHolds", self.as_dbus_array())
        self._controller.switch_profile(profile)
        return cookie

    def has(self, cookie):
        return cookie in self._holds

    def remove(self, cookie):
        self._cancel(cookie)
        if len(self._holds) != 0:
            new_profile = self._effective_hold_profile()
        else:
            new_profile = self._controller.base_profile
        self._controller.switch_profile(new_profile)

    def clear(self):
        for cookie in self._holds:
            self._cancel(cookie)


class Controller(exports.interfaces.ExportableInterface):
    def __init__(self, bus, tuned_interface):
        super(Controller, self).__init__()
        self._bus = bus
        self._tuned_interface = tuned_interface
        self._profile_holds = ProfileHoldManager(self)
        self._performance_degraded = PerformanceDegraded.NONE
        self._cmd = commands()
        self._terminate = threading.Event()
        self._on_battery = False
        self.load_config()

    def upower_changed(self, interface, changed, invalidated):
        properties = dbus.Interface(self.proxy, dbus.PROPERTIES_IFACE)
        self._on_battery = bool(properties.Get(UPOWER_DBUS_INTERFACE, "OnBattery"))
        tuned_profile = self._config.ppd_to_tuned_battery[self._base_profile] if self._on_battery else self._config.ppd_to_tuned[self._base_profile]
        log.info("Switching to profile '%s' due to battery %s" % (tuned_profile, self._on_battery))
        self._tuned_interface.switch_profile(tuned_profile)

    def setup_battery_signaling(self):
        try:
            bus = dbus.SystemBus()
            self.proxy = bus.get_object(UPOWER_DBUS_NAME, UPOWER_DBUS_PATH)
            self.proxy.connect_to_signal("PropertiesChanged", self.upower_changed)
            self.upower_changed(None, None, None)
        except dbus.exceptions.DBusException as error:
            log.debug(error)

    def _check_performance_degraded(self):
        performance_degraded = PerformanceDegraded.NONE
        if os.path.exists(NO_TURBO_PATH):
            if int(self._cmd.read_file(NO_TURBO_PATH)) == 1:
                performance_degraded = PerformanceDegraded.HIGH_OPERATING_TEMPERATURE
        if os.path.exists(LAP_MODE_PATH):
            if int(self._cmd.read_file(LAP_MODE_PATH)) == 1:
                performance_degraded = PerformanceDegraded.LAP_DETECTED
        if performance_degraded != self._performance_degraded:
            log.info("Performance degraded: %s" % performance_degraded)
            self._performance_degraded = performance_degraded
            exports.property_changed("PerformanceDegraded", performance_degraded)

    def run(self):
        exports.start()
        while not self._cmd.wait(self._terminate, 1):
            self._check_performance_degraded()
        exports.stop()

    @property
    def bus(self):
        return self._bus

    @property
    def base_profile(self):
        return self._base_profile

    def terminate(self):
        self._terminate.set()

    def load_config(self):
        self._config = PPDConfig(PPD_CONFIG_FILE)
        self._base_profile = self._config.default_profile
        self.switch_profile(self._config.default_profile)
        if self._config.battery_detection:
            self.setup_battery_signaling()

    def switch_profile(self, profile):
        if self.active_profile() == profile:
            return
        tuned_profile = self._config.ppd_to_tuned_battery[profile] if self._on_battery else self._config.ppd_to_tuned[profile]
        log.info("Switching to profile '%s'" % tuned_profile)
        self._tuned_interface.switch_profile(tuned_profile)
        exports.property_changed("ActiveProfile", profile)

    def active_profile(self):
        tuned_profile = self._tuned_interface.active_profile()
        return self._config.tuned_to_ppd.get(tuned_profile, "unknown")

    @exports.export("sss", "u")
    def HoldProfile(self, profile, reason, app_id, caller):
        if profile != PPD_POWER_SAVER and profile != PPD_PERFORMANCE:
            raise dbus.exceptions.DBusException(
                "Only '%s' and '%s' profiles may be held" % (PPD_POWER_SAVER, PPD_PERFORMANCE)
            )
        return self._profile_holds.add(profile, reason, app_id, caller)

    @exports.export("u", "")
    def ReleaseProfile(self, cookie, caller):
        if not self._profile_holds.has(cookie):
            raise dbus.exceptions.DBusException("No active hold for cookie '%s'" % cookie)
        self._profile_holds.remove(cookie)

    @exports.signal("u")
    def ProfileReleased(self, cookie):
        pass

    @exports.property_setter("ActiveProfile")
    def set_active_profile(self, profile):
        if profile not in self._config.ppd_to_tuned:
            raise dbus.exceptions.DBusException("Invalid profile '%s'" % profile)
        self._base_profile = profile
        self._profile_holds.clear()
        self.switch_profile(profile)

    @exports.property_getter("ActiveProfile")
    def get_active_profile(self):
        return self.active_profile()

    @exports.property_getter("Profiles")
    def get_profiles(self):
        return dbus.Array(
            [{"Profile": profile, "Driver": DRIVER} for profile in self._config.ppd_to_tuned.keys()],
            signature="a{sv}",
        )

    @exports.property_getter("Actions")
    def get_actions(self):
        return dbus.Array([], signature="s")

    @exports.property_getter("PerformanceDegraded")
    def get_performance_degraded(self):
        return self._performance_degraded

    @exports.property_getter("ActiveProfileHolds")
    def get_active_profile_holds(self):
        return self._profile_holds.as_dbus_array()
