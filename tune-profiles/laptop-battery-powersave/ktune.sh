#!/bin/sh

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
	# Set ALPM for all host adapters that support it
	set_alpm ${ALPM}

	# Enables USB autosuspend for all devices
	for i in /sys/bus/usb/devices/*/power/autosuspend; do echo 1 > $i; done > /dev/null 2>&1

	# Enables multi core power savings for low wakeup systems
	[ -e /sys/devices/system/cpu/sched_mc_power_savings ] && echo 1 > /sys/devices/system/cpu/sched_mc_power_savings

	# Enable ondemand governor (best for powersaving)
	[ -e /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ] && echo ondemand > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

	# Enable AC97 audio power saving
	[ -e /sys/module/snd_ac97_codec/parameters/power_save ] && echo Y > /sys/module/snd_ac97_codec/parameters/power_save

	# Disable HAL polling of CDROMS
	for i in /dev/scd*; do hal-disable-polling --device $i; done > /dev/null 2>&1

	# Enable power saving mode for Wi-Fi cards
	for i in /sys/bus/pci/devices/*/power_level ; do echo 5 > $i ; done > /dev/null 2>&1

	return 0
}

stop() {
	set_alpm "max_performance"

	# Disables USB autosuspend for all devices
	for i in /sys/bus/usb/devices/*/power/autosuspend; do echo 0 > $i; done > /dev/null 2>&1

	# Disables multi core power savings for low wakeup systems
	[ -e /sys/devices/system/cpu/sched_mc_power_savings ] && echo 0 > /sys/devices/system/cpu/sched_mc_power_savings

	# Enable ondemand governor (best for powersaving)
	[ -e /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ] && echo ondemand > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

	# Enable AC97 audio power saving
	[ -e /sys/module/snd_ac97_codec/parameters/power_save ] && echo Y > /sys/module/snd_ac97_codec/parameters/power_save

	# Enable HAL polling of CDROMS
	for i in /dev/scd*; do hal-disable-polling --enable-polling --device $i; done > /dev/null 2>&1

	# Reset power saving mode for Wi-Fi cards
	for i in /sys/bus/pci/devices/*/power_level ; do echo 0 > $i ; done > /dev/null 2>&1

	return 0
}

reload() {
	start
}

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
