from tuned.utils.config_parser import ConfigParser, Error
from tuned.exceptions import TunedException
import os

PPD_POWER_SAVER = "power-saver"
PPD_BALANCED = "balanced"
PPD_PERFORMANCE = "performance"

MAIN_SECTION = "main"
PROFILES_SECTION = "profiles"
BATTERY_SECTION = "battery"
DEFAULT_PROFILE_OPTION = "default"
BATTERY_DETECTION_OPTION = "battery_detection"
THINKPAD_FUNCTION_KEYS_OPTION = "thinkpad_function_keys"


class ProfileMap:
    """
    Mapping of PPD profiles to TuneD profiles or vice versa.
    """
    def __init__(self, ac_map, dc_map):
        self._ac_map = ac_map
        self._dc_map = dc_map

    def get(self, profile, on_battery):
        """
        Returns a TuneD profile corresponding to the given
        PPD profile and power supply status (or vice versa).
        """
        profile_map = self._dc_map if on_battery else self._ac_map
        return profile_map[profile]

    def keys(self, on_battery):
        """
        Returns the supported PPD or TuneD profiles.
        """
        profile_map = self._dc_map if on_battery else self._ac_map
        return profile_map.keys()


class PPDConfig:
    """
    Configuration for the tuned-ppd daemon.
    """
    def __init__(self, config_file, tuned_interface):
        self._tuned_interface = tuned_interface
        self.load_from_file(config_file)

    @property
    def battery_detection(self):
        """
        Whether battery detection is enabled.
        """
        return self._battery_detection

    @property
    def default_profile(self):
        """
        Default PPD profile to set during initialization.
        """
        return self._default_profile

    @property
    def ppd_to_tuned(self):
        """
        Mapping of PPD profiles to TuneD profiles.
        """
        return self._ppd_to_tuned

    @property
    def tuned_to_ppd(self):
        """
        Mapping of TuneD profiles to PPD profiles.
        """
        return self._tuned_to_ppd

    @property
    def thinkpad_function_keys(self):
        """
        Whether to react to changes of ACPI platform profile
        done via function keys (e.g., Fn-L) on newer Thinkpad
        machines. Experimental feature.
        """
        return self._thinkpad_function_keys

    def load_from_file(self, config_file):
        """
        Loads the configuration from the provided file.
        """
        cfg = ConfigParser()

        if not os.path.isfile(config_file):
            raise TunedException("Configuration file '%s' does not exist" % config_file)
        try:
            cfg.read(config_file)
        except Error:
            raise TunedException("Error parsing the configuration file '%s'" % config_file)

        if PROFILES_SECTION not in cfg:
            raise TunedException("Missing profiles section in the configuration file '%s'" % config_file)
        profile_dict_ac = dict(cfg[PROFILES_SECTION])

        if PPD_POWER_SAVER not in profile_dict_ac:
            raise TunedException("Missing power-saver profile in the configuration file '%s'" % config_file)

        if PPD_BALANCED not in profile_dict_ac:
            raise TunedException("Missing balanced profile in the configuration file '%s'" % config_file)

        if PPD_PERFORMANCE not in profile_dict_ac:
            raise TunedException("Missing performance profile in the configuration file '%s'" % config_file)

        if MAIN_SECTION not in cfg or DEFAULT_PROFILE_OPTION not in cfg[MAIN_SECTION]:
            self._default_profile = PPD_BALANCED
        else:
            self._default_profile = cfg[MAIN_SECTION][DEFAULT_PROFILE_OPTION]

        if self._default_profile not in profile_dict_ac:
            raise TunedException("Default profile '%s' missing in the profile mapping" % self._default_profile)

        self._battery_detection = cfg.getboolean(MAIN_SECTION, BATTERY_DETECTION_OPTION, fallback=BATTERY_SECTION in cfg)

        if self._battery_detection and BATTERY_SECTION not in cfg:
            raise TunedException("Missing battery section in the configuration file '%s'" % config_file)

        profile_dict_dc = profile_dict_ac | dict(cfg[BATTERY_SECTION]) if self._battery_detection else profile_dict_ac

        # Make sure all of the TuneD profiles specified in the configuration file actually exist
        unknown_tuned_profiles = (set(profile_dict_ac.values()) | set(profile_dict_dc.values())) - set(self._tuned_interface.profiles())
        if unknown_tuned_profiles:
            raise TunedException("Unknown TuneD profiles in the configuration file: " + ", ".join(unknown_tuned_profiles))

        # Make sure there are no PPD profiles appearing in the battery section which are not defined before
        unknown_battery_profiles = set(profile_dict_dc.keys()) - set(profile_dict_ac.keys())
        if unknown_battery_profiles:
            raise TunedException("Unknown PPD profiles in the battery section: " + ", ".join(unknown_battery_profiles))

        # Make sure the profile mapping is injective so it can be reverted
        if len(set(profile_dict_ac.values())) != len(profile_dict_ac) or len(set(profile_dict_dc.values())) != len(profile_dict_dc):
            raise TunedException("Duplicate profile mapping in the configuration file '%s'" % config_file)

        self._ppd_to_tuned = ProfileMap(profile_dict_ac, profile_dict_dc)
        self._tuned_to_ppd = ProfileMap({v: k for k, v in profile_dict_ac.items()}, {v: k for k, v in profile_dict_dc.items()})

        self._thinkpad_function_keys = cfg.getboolean(MAIN_SECTION, THINKPAD_FUNCTION_KEYS_OPTION, fallback=False)
