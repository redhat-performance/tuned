from tuned.utils.config_parser import ConfigParser, Error
from tuned.exceptions import TunedException
import os

PPD_POWER_SAVER = "power-saver"
PPD_PERFORMANCE = "performance"

MAIN_SECTION = "main"
PROFILES_SECTION = "profiles"
BATTERY_SECTION = "battery"
DEFAULT_PROFILE_OPTION = "default"
BATTERY_DETECTION_OPTION = "battery_detection"


class ProfileMap:
    def __init__(self, ac_map, dc_map):
        self._ac_map = ac_map
        self._dc_map = dc_map

    def get(self, profile, on_battery):
        if on_battery and profile in self._dc_map:
            return self._dc_map[profile]
        return self._ac_map[profile]

    def keys(self):
        return self._ac_map.keys()


class PPDConfig:
    def __init__(self, config_file):
        self.load_from_file(config_file)

    @property
    def battery_detection(self):
        return self._battery_detection

    @property
    def default_profile(self):
        return self._default_profile

    @property
    def ppd_to_tuned(self):
        return self._ppd_to_tuned

    def load_from_file(self, config_file):
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

        if not all(isinstance(mapped_profile, str) for mapped_profile in profile_dict_ac.values()):
            raise TunedException("Invalid profile mapping in the configuration file '%s'" % config_file)

        if PPD_POWER_SAVER not in profile_dict_ac:
            raise TunedException("Missing power-saver profile in the configuration file '%s'" % config_file)

        if PPD_PERFORMANCE not in profile_dict_ac:
            raise TunedException("Missing performance profile in the configuration file '%s'" % config_file)

        if MAIN_SECTION not in cfg or DEFAULT_PROFILE_OPTION not in cfg[MAIN_SECTION]:
            raise TunedException("Missing default profile in the configuration file '%s'" % config_file)

        self._default_profile = cfg[MAIN_SECTION][DEFAULT_PROFILE_OPTION]
        if self._default_profile not in profile_dict_ac:
            raise TunedException("Unknown default profile '%s'" % self._default_profile)

        if BATTERY_DETECTION_OPTION not in cfg[MAIN_SECTION]:
            raise TunedException("Missing battery detection option in the configuration file '%s'" % config_file)

        self._battery_detection = cfg.getboolean(MAIN_SECTION, BATTERY_DETECTION_OPTION)

        if self._battery_detection:
            if BATTERY_SECTION not in cfg:
                raise TunedException("Missing battery section in the configuration file '%s'" % config_file)
            profile_dict_dc = dict(cfg[BATTERY_SECTION])
        else:
            profile_dict_dc = {}

        self._ppd_to_tuned = ProfileMap(profile_dict_ac, profile_dict_dc)
