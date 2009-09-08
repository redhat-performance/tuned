#!/bin/sh

ALPM="medium_power"

# Set ALPM for all host adapters that support it
set_alpm() {
	for x in /sys/bus/scsi/devices/host*/scsi_host/host*/; do
		hotplug="0"
		if [ -e $x/sata_hotplug ]; then
			hotplug="$(cat $x/sata_hotplug)"
		fi
		if [ "$hotplug" == "0" -a -e $x/link_power_management_policy ]; then
			echo $1 > $x/link_power_management_policy
		fi
	done
}

start() {
	set_alpm ${ALPM}
	return 0
}

# Disable ALPM for all host adapters that support it
stop() {
	set_alpm "max_power"
	return 0
}

# Reload it, just start once more
reload() {
	start
}

# Status
status() {
	return 0
}


case "$1" in
    start)
        [ -f "$VAR_SUBSYS_KTUNE" ] && exit 0
        start
        RETVAL=$?
        ;;
    stop)
        [ -f "$VAR_SUBSYS_KTUNE" ] || exit 0
        stop
        RETVAL=$?
        ;;
    reload)
        [ -f "$VAR_SUBSYS_KTUNE" ] && reload
        RETVAL=$?
        ;;
    restart|force-reload)
        [ -f "$VAR_SUBSYS_KTUNE" ] && stop
        start
        RETVAL=$?
        ;;
    condrestart|try-restart)
        [ -f "$VAR_SUBSYS_KTUNE" ] || exit 0
        stop
        start
        RETVAL=$?
        ;;
    status)
        status
        RETVAL=$?
        ;;
    *)
        echo $"Usage: $0 {start|stop|restart|condrestart|status}"
        RETVAL=2
        ;;
esac
