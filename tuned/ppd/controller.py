from tuned import exports, logs
from tuned.utils.commands import commands
from tuned.consts import PPD_CONFIG_FILE, PPD_BASE_PROFILE_FILE, PPD_API_COMPATIBILITY
from tuned.ppd.config import PPDConfig, PPD_PERFORMANCE, PPD_BALANCED, PPD_POWER_SAVER

from enum import StrEnum
import pyinotify
import threading
import dbus
import os
import time

log = logs.get()

DRIVER = "tuned"
NO_TURBO_PATH = "/sys/devices/system/cpu/intel_pstate/no_turbo"
LAP_MODE_PATH = "/sys/bus/platform/devices/thinkpad_acpi/dytc_lapmode"
UNKNOWN_PROFILE = "unknown"

UPOWER_DBUS_NAME = "org.freedesktop.UPower"
UPOWER_DBUS_PATH = "/org/freedesktop/UPower"
UPOWER_DBUS_INTERFACE = "org.freedesktop.UPower"

PLATFORM_PROFILE_PATH = "/sys/firmware/acpi/platform_profile"
PLATFORM_PROFILE_MAPPING = {
    "low-power": PPD_POWER_SAVER,
    "balanced": PPD_BALANCED,
    "performance": PPD_PERFORMANCE
}


class PerformanceDegraded(StrEnum):
    """
    Possible reasons for performance degradation.
    """
    NONE = ""
    LAP_DETECTED = "lap-detected"
    HIGH_OPERATING_TEMPERATURE = "high-operating-temperature"


class PerformanceDegradedEventHandler(pyinotify.ProcessEvent):
    """
    Event handler for checking performance degradation.
    """
    def __init__(self, controller, path):
        super(PerformanceDegradedEventHandler, self).__init__()
        self._controller = controller
        self._path = path

    def process_IN_MODIFY(self, event):
        if event.pathname != self._path:
            return
        self._controller.check_performance_degraded()


class PlatformProfileEventHandler(pyinotify.ProcessEvent):
    """
    Event handler for switching PPD profiles based on the
    ACPI platform profile

    This handler should only invoke a PPD profile change if the
    change of the file at PLATFORM_PROFILE_PATH comes from within
    the kernel (e.g., when the user presses Fn-L on a Thinkpad laptop).
    This is currently detected as the file being modified without
    being opened before.
    """
    CLOSE_MODIFY_BUFFER = 0.1

    def __init__(self, controller):
        super(PlatformProfileEventHandler, self).__init__()
        self._controller = controller
        self._file_open = False
        self._last_close = 0

    def process_IN_OPEN(self, event):
        if event.pathname != PLATFORM_PROFILE_PATH:
            return
        self._file_open = True
        self._last_close = 0

    def process_IN_CLOSE_WRITE(self, event):
        if event.pathname != PLATFORM_PROFILE_PATH:
            return
        self._file_open = False
        self._last_close = time.time()

    def process_IN_CLOSE_NOWRITE(self, event):
        if event.pathname != PLATFORM_PROFILE_PATH:
            return
        self._file_open = False

    def process_IN_MODIFY(self, event):
        if event.pathname != PLATFORM_PROFILE_PATH or self._file_open or self._last_close + self.CLOSE_MODIFY_BUFFER > time.time():
            # Do not invoke a profile change if a modify event comes:
            # 1. when the file is open,
            # 2. directly after the file is closed (the events may sometimes come in the wrong order).
            return
        self._controller.check_platform_profile()


class ProfileHold(object):
    """
    Class holding information about a single profile hold,
    i.e., a temporary profile switch requested by a process.
    """
    def __init__(self, profile, reason, app_id, watch):
        self.profile = profile
        self.reason = reason
        self.app_id = app_id
        self.watch = watch

    def as_dict(self):
        """
        Returns the hold information as a Python dictionary.
        """
        return {
            "Profile": self.profile,
            "Reason": self.reason,
            "ApplicationId": self.app_id,
        }


class ProfileHoldManager(object):
    """
    Manager of profile holds responsible for their creation/deletion
    and for choosing the effective one. Holds are identified using
    integer cookies which are distributed to the hold-requesting processes.
    """
    def __init__(self, controller):
        self._holds = {}
        self._cookie_counter = 0
        self._controller = controller

    def _removal_callback(self, cookie, app_id):
        """
        Returns the callback to invoke when the process with the given ID
        (which requested a hold with the given cookie) disappears.
        """
        def callback(name):
            if name == "":
                log.info("Application '%s' disappeared, releasing hold '%s'" % (app_id, cookie))
                self.remove(cookie)

        return callback

    def _effective_hold_profile(self):
        """
        Returns the hold to use from the set of all active ones.
        """
        if any(hold.profile == PPD_POWER_SAVER for hold in self._holds.values()):
            return PPD_POWER_SAVER
        return PPD_PERFORMANCE

    def _cancel(self, cookie):
        """
        Cancels the hold saved under the provided cookie.
        """
        if cookie not in self._holds:
            return
        hold = self._holds.pop(cookie)
        hold.watch.cancel()
        exports.send_signal("ProfileReleased", cookie)
        exports.property_changed("ActiveProfileHolds", self.as_dbus_array())
        log.info("Releasing hold '%s': profile '%s' by application '%s'" % (cookie, hold.profile, hold.app_id))

    def as_dbus_array(self):
        """
        Returns the information about current holds as a DBus-compatible array.
        """
        return dbus.Array([hold.as_dict() for hold in self._holds.values()], signature="a{sv}")

    def add(self, profile, reason, app_id, caller):
        """
        Adds a new profile hold.
        """
        cookie = self._cookie_counter
        self._cookie_counter += 1
        watch = self._controller.bus.watch_name_owner(caller, self._removal_callback(cookie, app_id))
        log.info("Adding hold '%s': profile '%s' by application '%s'" % (cookie, profile, app_id))
        self._holds[cookie] = ProfileHold(profile, reason, app_id, watch)
        exports.property_changed("ActiveProfileHolds", self.as_dbus_array())
        self._controller.switch_profile(profile)
        return cookie

    def has(self, cookie):
        """
        Returns True if there is a hold under the given cookie.
        """
        return cookie in self._holds

    def remove(self, cookie):
        """
        Releases the hold saved under the provided cookie and
        sets the next profile.
        """
        self._cancel(cookie)
        if len(self._holds) != 0:
            new_profile = self._effective_hold_profile()
        else:
            new_profile = self._controller.base_profile
        self._controller.switch_profile(new_profile)

    def clear(self):
        """
        Releases all profile holds.
        """
        for cookie in list(self._holds.keys()):
            self._cancel(cookie)


class Controller(exports.interfaces.ExportableInterface):
    """
    The main tuned-ppd controller, exporting its DBus interface.
    """
    def __init__(self, bus, tuned_interface):
        super(Controller, self).__init__()
        self._bus = bus
        self._tuned_interface = tuned_interface
        self._cmd = commands()
        self._terminate = threading.Event()
        self._battery_handler = None
        self._on_battery = False
        self._watch_manager = pyinotify.WatchManager()
        self._notifier = pyinotify.ThreadedNotifier(self._watch_manager)
        self._inotify_watches = {}
        self._platform_profile_supported = os.path.isfile(PLATFORM_PROFILE_PATH)
        self._no_turbo_supported = os.path.isfile(NO_TURBO_PATH)
        self._lap_mode_supported = os.path.isfile(LAP_MODE_PATH)
        self._tuned_interface.connect_to_signal("profile_changed", self._tuned_profile_changed)
        self.initialize()

    def _upower_changed(self, interface, changed, invalidated):
        """
        The callback to invoke when the power supply changes.
        """
        self._on_battery = bool(self._upower_properties.Get(UPOWER_DBUS_INTERFACE, "OnBattery"))
        log.info("Battery status changed: " + ("DC (battery)" if self._on_battery else "AC (charging)"))
        self.switch_profile(self._active_profile)

    def _tuned_profile_changed(self, tuned_profile, result, errstr):
        """
        The callback to invoke when TuneD signals a profile change.
        """
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
        """
        Sets up handling of power supply changes.
        """
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

    def _setup_inotify(self):
        """
        Sets up inotify file watches.
        """
        self._watch_manager.rm_watch(list(self._inotify_watches.values()))
        if self._no_turbo_supported:
            self._inotify_watches |= self._watch_manager.add_watch(path=os.path.dirname(NO_TURBO_PATH),
                                                                   mask=pyinotify.IN_MODIFY,
                                                                   proc_fun=PerformanceDegradedEventHandler(NO_TURBO_PATH, self))
        if self._lap_mode_supported:
            self._inotify_watches |= self._watch_manager.add_watch(path=os.path.dirname(LAP_MODE_PATH),
                                                                   mask=pyinotify.IN_MODIFY,
                                                                   proc_fun=PerformanceDegradedEventHandler(LAP_MODE_PATH, self))
        if self._platform_profile_supported and self._config.thinkpad_function_keys:
           self._inotify_watches |= self._watch_manager.add_watch(path=os.path.dirname(PLATFORM_PROFILE_PATH),
                                                                  mask=pyinotify.IN_OPEN | pyinotify.IN_MODIFY | pyinotify.IN_CLOSE_WRITE | pyinotify.IN_CLOSE_NOWRITE,
                                                                  proc_fun=PlatformProfileEventHandler(self))

    def check_performance_degraded(self):
        """
        Checks the current performance degradation status and sends a signal if it changed.
        """
        performance_degraded = PerformanceDegraded.NONE
        if os.path.exists(NO_TURBO_PATH) and self._cmd.read_file(NO_TURBO_PATH).strip() == "1":
            performance_degraded = PerformanceDegraded.HIGH_OPERATING_TEMPERATURE
        if os.path.exists(LAP_MODE_PATH) and self._cmd.read_file(LAP_MODE_PATH).strip() == "1":
            performance_degraded = PerformanceDegraded.LAP_DETECTED
        if performance_degraded != self._performance_degraded:
            log.info("Performance degraded: %s" % performance_degraded)
            self._performance_degraded = performance_degraded
            exports.property_changed("PerformanceDegraded", performance_degraded)

    def check_platform_profile(self):
        """
        Sets the active PPD profile based on the content of the ACPI platform profile.
        """
        platform_profile = self._cmd.read_file(PLATFORM_PROFILE_PATH).strip()
        if platform_profile not in PLATFORM_PROFILE_MAPPING:
            return
        log.debug("Platform profile changed: %s" % platform_profile)
        new_profile = PLATFORM_PROFILE_MAPPING[platform_profile]
        self._profile_holds.clear()
        self.switch_profile(new_profile)
        self._base_profile = new_profile
        self._save_base_profile(new_profile)

    def _load_base_profile(self):
        """
        Loads and returns the saved PPD base profile.
        """
        return self._cmd.read_file(PPD_BASE_PROFILE_FILE, no_error=True).strip() or None

    def _save_base_profile(self, profile):
        """
        Saves the given PPD profile into the base profile file.
        """
        self._cmd.write_to_file(PPD_BASE_PROFILE_FILE, profile + "\n")

    def _set_tuned_profile(self, tuned_profile):
        """
        Sets the TuneD profile to the given one if not already set.
        """
        active_tuned_profile = self._tuned_interface.active_profile()
        if active_tuned_profile == tuned_profile:
            return True
        log.info("Setting TuneD profile to '%s'" % tuned_profile)
        ok, error_msg = self._tuned_interface.switch_profile(tuned_profile)
        if not ok:
            log.error(str(error_msg))
        return bool(ok)

    def initialize(self):
        """
        Initializes the controller.
        """
        self._active_profile = None
        self._profile_holds = ProfileHoldManager(self)
        self._performance_degraded = PerformanceDegraded.NONE
        self.check_performance_degraded()
        self._config = PPDConfig(PPD_CONFIG_FILE, self._tuned_interface)
        self._setup_battery_signaling()
        self._base_profile = self._load_base_profile() or self._config.default_profile
        self.switch_profile(self._base_profile)
        self._save_base_profile(self._base_profile)
        self._setup_inotify()

    def run(self):
        """
        Exports the DBus interface and runs the main daemon loop.
        """
        exports.start()
        self._notifier.start()
        while not self._cmd.wait(self._terminate, 1):
            pass
        self._watch_manager.rm_watch(list(self._inotify_watches.values()))
        self._notifier.stop()
        exports.stop()

    @property
    def bus(self):
        """
        DBus interface for communication with other services.
        """
        return self._bus

    @property
    def base_profile(self):
        """
        The base PPD profile. This is the profile to restore when
        all profile holds are released or when tuned-ppd is restarted.
        It may not be equal to the currently active profile.
        """
        return self._base_profile

    def terminate(self):
        """
        Stops the main loop of the daemon.
        """
        self._terminate.set()

    def switch_profile(self, profile):
        """
        Sets the currently active profile to the given one, if not already set.
        Does not change the base profile.
        """
        if not self._set_tuned_profile(self._config.ppd_to_tuned.get(profile, self._on_battery)):
            return False
        if self._active_profile != profile:
            exports.property_changed("ActiveProfile", profile)
            self._active_profile = profile
        return True

    @exports.export("sss", "u")
    def HoldProfile(self, profile, reason, app_id, caller):
        """
        Initiates a profile hold and returns a cookie for referring to it.
        """
        if profile != PPD_POWER_SAVER and profile != PPD_PERFORMANCE:
            raise dbus.exceptions.DBusException(
                "Only '%s' and '%s' profiles may be held" % (PPD_POWER_SAVER, PPD_PERFORMANCE)
            )
        return self._profile_holds.add(profile, reason, app_id, caller)

    @exports.export("u", "")
    def ReleaseProfile(self, cookie, caller):
        """
        Releases a held profile with the given cookie.
        """
        if not self._profile_holds.has(cookie):
            raise dbus.exceptions.DBusException("No active hold for cookie '%s'" % cookie)
        self._profile_holds.remove(cookie)

    @exports.signal("u")
    def ProfileReleased(self, cookie):
        """
        The DBus signal sent when a held profile is released.
        """
        pass

    @exports.property_setter("ActiveProfile")
    def set_active_profile(self, profile):
        """
        Sets the base profile to the given one and also makes it active.
        If there are any active profile holds, these are cancelled.
        """
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
        """
        Returns the currently active PPD profile.
        """
        return self._active_profile

    @exports.property_getter("Profiles")
    def get_profiles(self):
        """
        Returns a DBus array of all available PPD profiles.
        """
        return dbus.Array(
            [{"Profile": profile, "Driver": DRIVER} for profile in self._config.ppd_to_tuned.keys(self._on_battery)],
            signature="a{sv}",
        )

    @exports.property_getter("Actions")
    def get_actions(self):
        """
        Returns a DBus array of all available actions (currently there are none).
        """
        return dbus.Array([], signature="s")

    @exports.property_getter("PerformanceDegraded")
    def get_performance_degraded(self):
        """
        Returns the current performance degradation status.
        """
        return self._performance_degraded

    @exports.property_getter("ActiveProfileHolds")
    def get_active_profile_holds(self):
        """
        Returns a DBus array of active profile holds.
        """
        return self._profile_holds.as_dbus_array()

    @exports.property_getter("Version")
    def version(self):
        return PPD_API_COMPATIBILITY
