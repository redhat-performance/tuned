GLOBAL_CONFIG_FILE = "/etc/tuned/tuned-main.conf"
ACTIVE_PROFILE_FILE = "/etc/tuned/active_profile"
AUTODETECT_FILE = "recommend.conf"
DAEMONIZE_PARENT_TIMEOUT = 5
DBUS_BUS = "com.redhat.tuned"
DBUS_INTERFACE = "com.redhat.tuned.control"
DBUS_OBJECT = "/Tuned"
DEFAULT_PROFILE = "balanced"
DEFAULT_STORAGE_FILE = "/run/tuned/save.pickle"
LOAD_DIRECTORIES = ["/usr/lib/tuned", "/etc/tuned"]

# max. number of consecutive errors to give up
ERROR_THRESHOLD = 3

# bootloader plugin configuration
GRUB2_CFG_FILES = ["/boot/grub2/grub.cfg", "/boot/efi/EFI/redhat/grub.cfg", "/boot/efi/EFI/fedora/grub.cfg"]
GRUB2_CFG_DIR = "/etc/grub.d"
GRUB2_TUNED_TEMPLATE_NAME = "00_tuned"
GRUB2_TUNED_TEMPLATE_PATH = GRUB2_CFG_DIR + "/" + GRUB2_TUNED_TEMPLATE_NAME
GRUB2_TEMPLATE_HEADER_BEGIN = "### BEGIN /etc/grub.d/" + GRUB2_TUNED_TEMPLATE_NAME +  " ###"
GRUB2_TEMPLATE_HEADER_END = "### END /etc/grub.d/" + GRUB2_TUNED_TEMPLATE_NAME +  " ###"
GRUB2_TUNED_VAR = "tuned_params"
GRUB2_DEFAULT_ENV_FILE = "/etc/default/grub"
BOOT_CMDLINE_TUNED_VAR = "TUNED_BOOT_CMDLINE"
BOOT_CMDLINE_FILE = "/etc/tuned/bootcmdline"

# number of backups
LOG_FILE_COUNT = 2
LOG_FILE_MAXBYTES = 100*1000
LOG_FILE = "/var/log/tuned/tuned.log"
PID_FILE = "/run/tuned/tuned.pid"
SYSTEM_RELEASE_FILE = "/etc/system-release-cpe"
# prefix for functions plugins
FUNCTION_PREFIX = "function_"
# prefix for exported environment variables when calling scripts
ENV_PREFIX = "TUNED_"

# tuned-gui
PREFIX_PROFILE_FACTORY = "Factory"
PREFIX_PROFILE_USER = "User"

CFG_DAEMON = "daemon"
CFG_DYNAMIC_TUNING = "dynamic_tuning"
CFG_SLEEP_INTERVAL = "sleep_interval"
CFG_UPDATE_INTERVAL = "update_interval"
CFG_RECOMMEND_COMMAND = "recommend_command"

# no_daemon mode
CFG_DEF_DAEMON = True
# default configuration
CFG_DEF_DYNAMIC_TUNING = True
# how long to sleep before checking for events (in seconds)
CFG_DEF_SLEEP_INTERVAL = 1
# update interval for dynamic tuning (in seconds)
CFG_DEF_UPDATE_INTERVAL = 10
# recommend command availability
CFG_DEF_RECOMMEND_COMMAND = True

STR_VERIFY_PROFILE_DEVICE_VALUE_OK = "verify: passed: device %s: %s = %s"
STR_VERIFY_PROFILE_VALUE_OK = "verify: passed: %s = %s"
STR_VERIFY_PROFILE_OK = "verify: passed: %s"
STR_VERIFY_PROFILE_DEVICE_VALUE_FAIL = "verify: failed: device %s: %s = %s, expected %s"
STR_VERIFY_PROFILE_VALUE_FAIL = "verify: failed: %s = %s, expected %s"
STR_VERIFY_PROFILE_FAIL = "verify: failed: %s"
