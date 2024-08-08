import logging

GLOBAL_CONFIG_FILE = "/etc/tuned/tuned-main.conf"
ACTIVE_PROFILE_FILE = "/etc/tuned/active_profile"
PROFILE_MODE_FILE = "/etc/tuned/profile_mode"
POST_LOADED_PROFILE_FILE = "/etc/tuned/post_loaded_profile"
PROFILE_FILE = "tuned.conf"
RECOMMEND_CONF_FILE = "/etc/tuned/recommend.conf"
DAEMONIZE_PARENT_TIMEOUT = 5
NAMESPACE = "com.redhat.tuned"
DBUS_BUS = NAMESPACE
DBUS_INTERFACE = "com.redhat.tuned.control"
DBUS_OBJECT = "/Tuned"
DEFAULT_PROFILE = "balanced"
DEFAULT_STORAGE_FILE = "/run/tuned/save.pickle"
SYSTEM_PROFILE_DIR = "/usr/lib/tuned/profiles"
PERSISTENT_STORAGE_DIR = "/var/lib/tuned"
PLUGIN_MAIN_UNIT_NAME = "main"
# Magic section header because ConfigParser does not support "headerless" config
MAGIC_HEADER_NAME = "this_is_some_magic_section_header_because_of_compatibility"
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
BOOT_CMDLINE_KARGS_DELETED_VAR = "TUNED_BOOT_KARGS_DELETED"
BOOT_CMDLINE_FILE = "/etc/tuned/bootcmdline"
PETITBOOT_DETECT_DIR = "/sys/firmware/opal"
MACHINE_ID_FILE = "/etc/machine-id"
KERNEL_UPDATE_HOOK_FILE = "/usr/lib/kernel/install.d/92-tuned.install"
BLS_ENTRIES_PATH = "/boot/loader/entries"

# scheduler plugin configuration
# how many times retry to move tasks to parent cgroup on cgroup cleanup
CGROUP_CLEANUP_TASKS_RETRY = 10
PROCFS_MOUNT_POINT = "/proc"
DEF_CGROUP_MOUNT_POINT = "/sys/fs/cgroup/cpuset"
DEF_CGROUP_MODE = 0o770

# service plugin configuration
SERVICE_SYSTEMD_CFG_PATH = "/etc/systemd/system/%s.service.d"
DEF_SERVICE_CFG_DIR_MODE = 0o755

# modules plugin configuration
MODULES_FILE = "/etc/modprobe.d/tuned.conf"

# systemd plugin configuration
SYSTEMD_SYSTEM_CONF_FILE = "/etc/systemd/system.conf"
SYSTEMD_CPUAFFINITY_VAR = "CPUAffinity"

# irqbalance plugin configuration
IRQBALANCE_SYSCONFIG_FILE = "/etc/sysconfig/irqbalance"

# acpi plugin configuration
ACPI_DIR = "/sys/firmware/acpi"

# built-in functions configuration
SYSFS_CPUS_PATH = "/sys/devices/system/cpu"

# number of backups
LOG_FILE_COUNT = 2
LOG_FILE_MAXBYTES = 100*1000
LOG_FILE = "/var/log/tuned/tuned.log"
PPD_LOG_FILE = "/var/log/tuned/tuned-ppd.log"
PID_FILE = "/run/tuned/tuned.pid"
SYSTEM_RELEASE_FILE = "/etc/system-release-cpe"
# prefix for functions plugins
FUNCTION_PREFIX = "function_"
# prefix for exported environment variables when calling scripts
ENV_PREFIX = "TUNED_"
ROLLBACK_NONE = 0
ROLLBACK_SOFT = 1
ROLLBACK_FULL = 2

# tuned-gui
PREFIX_PROFILE_FACTORY = "System"
PREFIX_PROFILE_USER = "User"

# PPD-to-tuned API translation daemon configuration
PPD_NAMESPACE = "net.hadess.PowerProfiles"
PPD_DBUS_BUS = PPD_NAMESPACE
PPD_DBUS_OBJECT = "/net/hadess/PowerProfiles"
PPD_DBUS_INTERFACE = PPD_DBUS_BUS
PPD_CONFIG_FILE = "/etc/tuned/ppd.conf"
PPD_BASE_PROFILE_FILE = "/etc/tuned/ppd_base_profile"

# After adding new option to tuned-main.conf add here its name with CFG_ prefix
# and eventually default value with CFG_DEF_ prefix (default is None)
# and function for check with CFG_FUNC_ prefix
# (see configobj for methods, default is get for string)
CFG_DAEMON = "daemon"
CFG_DYNAMIC_TUNING = "dynamic_tuning"
CFG_SLEEP_INTERVAL = "sleep_interval"
CFG_UPDATE_INTERVAL = "update_interval"
CFG_RECOMMEND_COMMAND = "recommend_command"
CFG_REAPPLY_SYSCTL = "reapply_sysctl"
CFG_DEFAULT_INSTANCE_PRIORITY = "default_instance_priority"
CFG_UDEV_BUFFER_SIZE = "udev_buffer_size"
CFG_LOG_FILE_COUNT = "log_file_count"
CFG_LOG_FILE_MAX_SIZE = "log_file_max_size"
CFG_UNAME_STRING = "uname_string"
CFG_CPUINFO_STRING = "cpuinfo_string"
CFG_ENABLE_DBUS = "enable_dbus"
CFG_ENABLE_UNIX_SOCKET = "enable_unix_socket"
CFG_UNIX_SOCKET_PATH = "unix_socket_path"
CFG_UNIX_SOCKET_SIGNAL_PATHS = "unix_socket_signal_paths"
CFG_UNIX_SOCKET_OWNERSHIP = "unix_socket_ownership"
CFG_UNIX_SOCKET_PERMISIONS = "unix_socket_permissions"
CFG_UNIX_SOCKET_CONNECTIONS_BACKLOG = "connections_backlog"
CFG_CPU_EPP_FLAG = "hwp_epp"
CFG_ROLLBACK = "rollback"
CFG_PROFILE_DIRS = "profile_dirs"

# no_daemon mode
CFG_DEF_DAEMON = True
CFG_FUNC_DAEMON = "getboolean"
# default configuration
CFG_DEF_DYNAMIC_TUNING = True
CFG_FUNC_DYNAMIC_TUNING = "getboolean"
# how long to sleep before checking for events (in seconds)
CFG_DEF_SLEEP_INTERVAL = 1
CFG_FUNC_SLEEP_INTERVAL = "getint"
# update interval for dynamic tuning (in seconds)
CFG_DEF_UPDATE_INTERVAL = 10
CFG_FUNC_UPDATE_INTERVAL = "getint"
# recommend command availability
CFG_DEF_RECOMMEND_COMMAND = True
CFG_FUNC_RECOMMEND_COMMAND = "getboolean"
# reapply system sysctl
CFG_DEF_REAPPLY_SYSCTL = True
CFG_FUNC_REAPPLY_SYSCTL = "getboolean"
# default instance priority
CFG_DEF_DEFAULT_INSTANCE_PRIORITY = 0
CFG_FUNC_DEFAULT_INSTANCE_PRIORITY = "getint"
# default pyudev.Monitor buffer size
CFG_DEF_UDEV_BUFFER_SIZE = 1024 * 1024
# default log file count
CFG_DEF_LOG_FILE_COUNT = 2
CFG_FUNC_LOG_FILE_COUNT = "getint"
# default log file max size
CFG_DEF_LOG_FILE_MAX_SIZE = 1024 * 1024
# default listening on dbus
CFG_DEF_ENABLE_DBUS = True
CFG_FUNC_ENABLE_DBUS = "getboolean"
# default listening on unix socket
# as it is not used commonly disabled by default
CFG_DEF_ENABLE_UNIX_SOCKET = False
CFG_FUNC_ENABLE_UNIX_SOCKET = "getboolean"
# default unix socket path
CFG_DEF_UNIX_SOCKET_PATH = "/run/tuned/tuned.sock"
CFG_DEF_UNIX_SOCKET_SIGNAL_PATHS = ""
# default unix socket ownership
# (uid and gid, python2 does not support names out of box, -1 leaves default)
CFG_DEF_UNIX_SOCKET_OWNERSHIP = "-1 -1"
# default unix socket permissions
CFG_DEF_UNIX_SOCKET_PERMISIONS = "0o600"
# default unix socket conections backlog
CFG_DEF_UNIX_SOCKET_CONNECTIONS_BACKLOG = "1024"
CFG_FUNC_UNIX_SOCKET_CONNECTIONS_BACKLOG = "getint"
# default rollback strategy
CFG_DEF_ROLLBACK = "auto"
# default profile directories
CFG_DEF_PROFILE_DIRS = [SYSTEM_PROFILE_DIR, "/etc/tuned/profiles"]

PATH_CPU_DMA_LATENCY = "/dev/cpu_dma_latency"

# profile attributes which can be specified in the main section
PROFILE_ATTR_SUMMARY = "summary"
PROFILE_ATTR_DESCRIPTION = "description"

SIGNAL_PROFILE_CHANGED = "profile_changed"

STR_HINT_REBOOT = "you need to reboot for changes to take effect"

STR_VERIFY_PROFILE_DEVICE_VALUE_OK = "verify: passed: device %s: '%s' = '%s'"
STR_VERIFY_PROFILE_VALUE_OK = "verify: passed: '%s' = '%s'"
STR_VERIFY_PROFILE_OK = "verify: passed: '%s'"
STR_VERIFY_PROFILE_DEVICE_VALUE_MISSING = "verify: skipped, missing: device %s: '%s'"
STR_VERIFY_PROFILE_VALUE_MISSING = "verify: skipped, missing: '%s'"
STR_VERIFY_PROFILE_DEVICE_VALUE_FAIL = "verify: failed: device %s: '%s' = '%s', expected '%s'"
STR_VERIFY_PROFILE_VALUE_FAIL = "verify: failed: '%s' = '%s', expected '%s'"
STR_VERIFY_PROFILE_CMDLINE_FAIL = "verify: failed: cmdline arg '%s', expected '%s'"
STR_VERIFY_PROFILE_CMDLINE_FAIL_MISSING = "verify: failed: cmdline arg '%s' is missing, expected '%s'"
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

# number of retries when waiting for device initialization
HOTPLUG_WAIT_FOR_DEV_INIT_RETRIES = 100
# how long to wait for device initialization in seconds during retry
HOTPLUG_WAIT_FOR_DEV_INIT_DELAY = 0.1
