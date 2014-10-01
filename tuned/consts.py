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
ERROR_THRESHOLD = 5

# bootloader plugin configuration
GRUB2_CFG_FILES = ["/boot/grub2/grub.cfg", "/boot/efi/EFI/redhat/grub.cfg", "/boot/efi/EFI/fedora/grub.cfg"]
GRUB2_TUNED_TEMPLATE_NAME = "00_tuned"
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

# tuned-gui
PREFIX_PROFILE_FACTORY = "Factory"
PREFIX_PROFILE_USER = "User"

# default configuration
CFG_DEF_DYNAMIC_TUNING = True
# how long to sleep before checking for events (in seconds)
CFG_DEF_SLEEP_INTERVAL = 1
# update interval for dynamic tuning (in seconds)
CFG_DEF_UPDATE_INTERVAL = 10
