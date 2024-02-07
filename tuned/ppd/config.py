from tuned.utils.config_parser import ConfigParser, Error
from tuned.exceptions import TunedException
import os

PPD_POWER_SAVER = "power-saver"
PPD_PERFORMANCE = "performance"

MAIN_SECTION = "main"
PROFILES_SECTION = "profiles"
DEFAULT_PROFILE_OPTION = "default"


class PPDConfig:
    def __init__(self, config_file):
        self.load_from_file(config_file)

    @property
    def default_profile(self):
        return self._default_profile

    @property
    def ppd_to_tuned(self):
        return self._ppd_to_tuned

    @property
    def tuned_to_ppd(self):
        return self._tuned_to_ppd

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
        self._ppd_to_tuned = dict(cfg[PROFILES_SECTION])

        if not all(isinstance(mapped_profile, str) for mapped_profile in self._ppd_to_tuned.values()):
            raise TunedException("Invalid profile mapping in the configuration file '%s'" % config_file)

        if len(set(self._ppd_to_tuned.values())) != len(self._ppd_to_tuned):
            raise TunedException("Duplicate profile mapping in the configuration file '%s'" % config_file)
        self._tuned_to_ppd = {v: k for k, v in self._ppd_to_tuned.items()}

        if PPD_POWER_SAVER not in self._ppd_to_tuned:
            raise TunedException("Missing power-saver profile in the configuration file '%s'" % config_file)

        if PPD_PERFORMANCE not in self._ppd_to_tuned:
            raise TunedException("Missing performance profile in the configuration file '%s'" % config_file)

        if MAIN_SECTION not in cfg or DEFAULT_PROFILE_OPTION not in cfg[MAIN_SECTION]:
            raise TunedException("Missing default profile in the configuration file '%s'" % config_file)

        self._default_profile = cfg[MAIN_SECTION][DEFAULT_PROFILE_OPTION]
        if self._default_profile not in self._ppd_to_tuned:
            raise TunedException("Unknown default profile '%s'" % self._default_profile)
