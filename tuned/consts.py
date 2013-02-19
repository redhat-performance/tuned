ACTIVE_PROFILE_FILE = "/etc/tuned/active_profile"
AUTODETECT_FILE = "recommend.conf"
DAEMONIZE_PARENT_TIMEOUT = 5
DBUS_BUS = "com.redhat.tuned"
DBUS_INTERFACE = "com.redhat.tuned.control"
DBUS_OBJECT = "/Tuned"
DEFAULT_PROFILE = "balanced"
LOAD_DIRECTORIES = ["/usr/lib/tuned", "/etc/tuned"]
# number of backups
LOG_FILE_COUNT = 2
LOG_FILE_MAXBYTES = 100*1000
LOG_FILE = "/var/log/tuned/tuned.log"
PID_FILE = "/run/tuned/tuned.pid"
SYSTEM_RELEASE_FILE = "/etc/system-release-cpe"
