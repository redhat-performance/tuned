#!/bin/sh

VAR_SUBSYS_KTUNE="/var/lock/subsys/ktune"

ALPM="min_power"

set_alpm() {
        for x in /sys/class/scsi_host/*; do
                if [ -f $x/ahci_port_cmd ]; then
                        port_cmd=`cat $x/ahci_port_cmd`;
                        if [ $((0x$port_cmd & 0x240000)) = 0 -a -f $x/link_power_management_policy ]; then
                                echo $1 >$x/link_power_management_policy;
                        else
                                echo "max_performance" >$x/link_power_management_policy;
                        fi
                fi
        done
}

start() {
	set_alpm ${ALPM}

	# Disable HAL polling of CDROMS
	for i in /dev/scd*; do hal-disable-polling --device $(readlink -f $i); done > /dev/null 2>&1

	return 0
}

stop() {
	set_alpm "max_performance"

        # Enable HAL polling of CDROMS
	for i in /dev/scd*; do hal-disable-polling --enable-polling --device $(readlink -f $i); done > /dev/null 2>&1

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
