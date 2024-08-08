from tuned import exports, logs
from tuned.utils.commands import commands
from tuned.consts import PPD_CONFIG_FILE, PPD_BASE_PROFILE_FILE
from tuned.ppd.config import PPDConfig, PPD_PERFORMANCE, PPD_POWER_SAVER
from enum import StrEnum
import threading
import dbus
import os

log = logs.get()

DRIVER = "tuned"
NO_TURBO_PATH = "/sys/devices/system/cpu/intel_pstate/no_turbo"
LAP_MODE_PATH = "/sys/bus/platform/devices/thinkpad_acpi/dytc_lapmode"
UNKNOWN_PROFILE = "unknown"

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
        for cookie in list(self._holds.keys()):
            self._cancel(cookie)


class Controller(exports.interfaces.ExportableInterface):
    def __init__(self, bus, tuned_interface):
        super(Controller, self).__init__()
        self._bus = bus
        self._tuned_interface = tuned_interface
        self._cmd = commands()
        self._terminate = threading.Event()
        self._battery_handler = None
        self._on_battery = False
        self._tuned_interface.connect_to_signal("profile_changed", self._tuned_profile_changed)
        self.initialize()

    def _upower_changed(self, interface, changed, invalidated):
        self._on_battery = bool(self._upower_properties.Get(UPOWER_DBUS_INTERFACE, "OnBattery"))
        log.info("Battery status changed: " + ("DC (battery)" if self._on_battery else "AC (charging)"))
        self.switch_profile(self._active_profile)

    def _tuned_profile_changed(self, tuned_profile, result, errstr):
        if not result:
            return
        self._profile_holds.clear()
        try:
            ppd_profile = self._config.tuned_to_ppd.get(tuned_profile, self._on_battery)
        except KeyError:
            ppd_profile = UNKNOWN_PROFILE
            log.warning("TuneD profile changed to an unknown profile '%s'" % tuned_profile)
        if self._active_profile != ppd_profile:
            log.info("Profile changed to '%s'" % ppd_profile)
            self._active_profile = ppd_profile
            exports.property_changed("ActiveProfile", self._active_profile)
            if ppd_profile != UNKNOWN_PROFILE:
                self._base_profile = ppd_profile
                self._save_base_profile(ppd_profile)

    def _setup_battery_signaling(self):
        self._on_battery = False
        if not self._config.battery_detection:
            if self._battery_handler is not None:
                self._battery_handler.remove()
                self._battery_handler = None
            return
        try:
            if self._battery_handler is None:
                upower_proxy = self._bus.get_object(UPOWER_DBUS_NAME, UPOWER_DBUS_PATH)
                self._upower_properties = dbus.Interface(upower_proxy, dbus.PROPERTIES_IFACE)
                self._battery_handler = upower_proxy.connect_to_signal("PropertiesChanged", self._upower_changed)
            self._on_battery = bool(self._upower_properties.Get(UPOWER_DBUS_INTERFACE, "OnBattery"))
        except dbus.exceptions.DBusException as error:
            log.debug(error)

    def _check_performance_degraded(self):
        performance_degraded = PerformanceDegraded.NONE
        if os.path.exists(NO_TURBO_PATH) and self._cmd.read_file(NO_TURBO_PATH).strip() == "1":
            performance_degraded = PerformanceDegraded.HIGH_OPERATING_TEMPERATURE
        if os.path.exists(LAP_MODE_PATH) and self._cmd.read_file(LAP_MODE_PATH).strip() == "1":
            performance_degraded = PerformanceDegraded.LAP_DETECTED
        if performance_degraded != self._performance_degraded:
            log.info("Performance degraded: %s" % performance_degraded)
            self._performance_degraded = performance_degraded
            exports.property_changed("PerformanceDegraded", performance_degraded)

    def _load_base_profile(self):
        return self._cmd.read_file(PPD_BASE_PROFILE_FILE, no_error=True).strip() or None

    def _save_base_profile(self, profile):
        self._cmd.write_to_file(PPD_BASE_PROFILE_FILE, profile + "\n")

    def _set_tuned_profile(self, tuned_profile):
        active_tuned_profile = self._tuned_interface.active_profile()
        if active_tuned_profile == tuned_profile:
            return True
        log.info("Setting TuneD profile to '%s'" % tuned_profile)
        ok, error_msg = self._tuned_interface.switch_profile(tuned_profile)
        if not ok:
            log.error(str(error_msg))
        return bool(ok)

    def initialize(self):
        self._active_profile = None
        self._profile_holds = ProfileHoldManager(self)
        self._performance_degraded = PerformanceDegraded.NONE
        self._config = PPDConfig(PPD_CONFIG_FILE, self._tuned_interface)
        self._setup_battery_signaling()
        self._base_profile = self._load_base_profile() or self._config.default_profile
        self.switch_profile(self._base_profile)
        self._save_base_profile(self._base_profile)

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

    def switch_profile(self, profile):
        if not self._set_tuned_profile(self._config.ppd_to_tuned.get(profile, self._on_battery)):
            return False
        if self._active_profile != profile:
            exports.property_changed("ActiveProfile", profile)
            self._active_profile = profile
        return True

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
        if profile not in self._config.ppd_to_tuned.keys(self._on_battery):
            raise dbus.exceptions.DBusException("Invalid profile '%s'" % profile)
        log.debug("Setting base profile to %s" % profile)
        self._profile_holds.clear()
        if not self.switch_profile(profile):
            raise dbus.exceptions.DBusException("Error setting profile %s'" % profile)
        self._base_profile = profile
        self._save_base_profile(profile)

    @exports.property_getter("ActiveProfile")
    def get_active_profile(self):
        return self._active_profile

    @exports.property_getter("Profiles")
    def get_profiles(self):
        return dbus.Array(
            [{"Profile": profile, "Driver": DRIVER} for profile in self._config.ppd_to_tuned.keys(self._on_battery)],
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
