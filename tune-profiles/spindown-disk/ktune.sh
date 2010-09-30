#!/bin/sh
# Author of original script: Daniel Mach
# Rewrite into profiles by: Marcela Mašláňová

VAR_SUBSYS_KTUNE="/var/lock/subsys/ktune"

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

remount() {
	OPTS=$1

    mount | grep 'type ext3 (' | while read LINE; do
		DEV=$(echo $LINE | sed 's@^\(.*\) on .* type .*$@\1@')
		MNT=$(echo $LINE | sed 's@^.* on \(.*\) type .*$@\1@')
		mount -o remount,$1 $DEV $MNT
    done
}


hdd_apm() {
	APM=$1

	for DEV in /dev/[sh]d[a-z]; do
		hdparm -B $APM $DEV >/dev/null 2>&1
	done
}


hdd_spindown() {
	SPINDOWN=$1

	for DEV in /dev/[sh]d[a-z]; do
		hdparm -S $SPINDOWN $DEV >/dev/null 2>&1
	done
}


wireless_powersave() {
	POWER=$1

	IFACES=$(cat /proc/net/wireless | grep -v '|' | sed 's@^ *\([^:]*\):.*@\1@')
	for IFACE in $IFACES; do
		iwpriv $IFACE set_power $POWER
	done
}

dont_sync_logs() {
	cp -p /etc/rsyslog.conf /etc/rsyslog.conf.bckp
	sed 's/ \/var\/log/-\/var\/log/' /etc/rsyslog.conf.bckp > /etc/rsyslog.conf
}

revert_logs() {
	mv /etc/rsyslog.conf.bckp /etc/rsyslog.conf
}

start() {
# redirect cron to tty8 isn't probably needed anymore

	set_alpm ${ALPM}
	# Enables USB autosuspend for all devices
	for i in /sys/bus/usb/devices/*/power/autosuspend; do echo 1 > $i; done
	# Disable HAL polling of CDROMS
	for i in /dev/scd*; do hal-disable-polling --device $(readlink -f $i); done
	hciconfig hci0 down; modprobe -r hci_usb
	dont_sync_logs
	wireless_powersave 1
	hdd_spindown 6
	hdd_apm 128
	remount commit=600,noatime
	find /etc/ >/dev/null 2>&1
	sync
	return 0
}

# Disable ALPM for all host adapters that support it
stop() {
	set_alpm "max_power"
	modprobe hci_usb; hciconfig hci0 up
	wireless_powersave 0
	revert_logs
	hdd_spindown 0
	hdd_apm 255
	remount commit=5
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
