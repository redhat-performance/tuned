import logging

GLOBAL_CONFIG_FILE = "/etc/tuned/tuned-main.conf"
ACTIVE_PROFILE_FILE = "/etc/tuned/active_profile"
PROFILE_MODE_FILE = "/etc/tuned/profile_mode"
PROFILE_FILE = "tuned.conf"
RECOMMEND_CONF_FILE = "/etc/tuned/recommend.conf"
DAEMONIZE_PARENT_TIMEOUT = 5
NAMESPACE = "com.redhat.tuned"
DBUS_BUS = NAMESPACE
DBUS_INTERFACE = "com.redhat.tuned.control"
DBUS_OBJECT = "/Tuned"
DEFAULT_PROFILE = "balanced"
DEFAULT_STORAGE_FILE = "/run/tuned/save.pickle"
LOAD_DIRECTORIES = ["/usr/lib/tuned", "/etc/tuned"]
PERSISTENT_STORAGE_DIR = "/var/lib/tuned"
PLUGIN_MAIN_UNIT_NAME = "main"
RECOMMEND_DIRECTORIES = ["/usr/lib/tuned/recommend.d", "/etc/tuned/recommend.d"]

TMP_FILE_SUFFIX = ".tmp"
# max. number of consecutive errors to give up
ERROR_THRESHOLD = 3

# bootloader plugin configuration
BOOT_DIR = "/boot"
GRUB2_CFG_FILES = ["/etc/grub2.cfg", "/etc/grub2-efi.cfg"]
GRUB2_CFG_DIR = "/etc/grub.d"
GRUB2_TUNED_TEMPLATE_NAME = "00_tuned"
GRUB2_TUNED_TEMPLATE_PATH = GRUB2_CFG_DIR + "/" + GRUB2_TUNED_TEMPLATE_NAME
GRUB2_TEMPLATE_HEADER_BEGIN = "### BEGIN /etc/grub.d/" + GRUB2_TUNED_TEMPLATE_NAME +  " ###"
GRUB2_TEMPLATE_HEADER_END = "### END /etc/grub.d/" + GRUB2_TUNED_TEMPLATE_NAME +  " ###"
GRUB2_TUNED_VAR = "tuned_params"
GRUB2_TUNED_INITRD_VAR = "tuned_initrd"
GRUB2_DEFAULT_ENV_FILE = "/etc/default/grub"
INITRD_IMAGE_DIR = "/boot"
BOOT_CMDLINE_TUNED_VAR = "TUNED_BOOT_CMDLINE"
BOOT_CMDLINE_INITRD_ADD_VAR = "TUNED_BOOT_INITRD_ADD"
BOOT_CMDLINE_FILE = "/etc/tuned/bootcmdline"
PETITBOOT_DETECT_DIR = "/sys/firmware/opal"

# modules plugin configuration
MODULES_FILE = "/etc/modprobe.d/tuned.conf"

# systemd plugin configuration
SYSTEMD_SYSTEM_CONF_FILE = "/etc/systemd/system.conf"
SYSTEMD_CPUAFFINITY_VAR = "CPUAffinity"

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
CFG_REAPPLY_SYSCTL = "reapply_sysctl"
CFG_DEFAULT_INSTANCE_PRIORITY = "default_instance_priority"
CFG_UDEV_BUFFER_SIZE = "udev_buffer_size"

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
# reapply system sysctl
CFG_DEF_REAPPLY_SYSCTL = True
# default instance priority
CFG_DEF_DEFAULT_INSTANCE_PRIORITY = 0
# default pyudev.Monitor buffer size
CFG_DEF_UDEV_BUFFER_SIZE = 1024 * 1024

PATH_CPU_DMA_LATENCY = "/dev/cpu_dma_latency"

# profile attributes which can be specified in the main section
PROFILE_ATTR_SUMMARY = "summary"
PROFILE_ATTR_DESCRIPTION = "description"

DBUS_SIGNAL_PROFILE_CHANGED = "profile_changed"

STR_HINT_REBOOT = "you need to reboot for changes to take effect"

STR_VERIFY_PROFILE_DEVICE_VALUE_OK = "verify: passed: device %s: '%s' = '%s'"
STR_VERIFY_PROFILE_VALUE_OK = "verify: passed: '%s' = '%s'"
STR_VERIFY_PROFILE_OK = "verify: passed: '%s'"
STR_VERIFY_PROFILE_DEVICE_VALUE_MISSING = "verify: skipped, missing: device %s: '%s'"
STR_VERIFY_PROFILE_VALUE_MISSING = "verify: skipped, missing: '%s'"
STR_VERIFY_PROFILE_DEVICE_VALUE_FAIL = "verify: failed: device %s: '%s' = '%s', expected '%s'"
STR_VERIFY_PROFILE_VALUE_FAIL = "verify: failed: '%s' = '%s', expected '%s'"
STR_VERIFY_PROFILE_FAIL = "verify: failed: '%s'"

# timout for tuned-adm operations in seconds
ADMIN_TIMEOUT = 600

# Strings for /etc/tuned/profile_mode specifying if the active profile
# was set automatically or manually
ACTIVE_PROFILE_AUTO = "auto"
ACTIVE_PROFILE_MANUAL = "manual"

LOG_LEVEL_CONSOLE = 60
LOG_LEVEL_CONSOLE_NAME = "CONSOLE"
CAPTURE_LOG_LEVEL = "console"
CAPTURE_LOG_LEVELS = {
		"debug": logging.DEBUG,
		"info": logging.INFO,
		"warn": logging.WARN,
		"error": logging.ERROR,
		"console": LOG_LEVEL_CONSOLE,
		"none": None,
		}
