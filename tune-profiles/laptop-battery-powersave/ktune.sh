#!/bin/sh

ALPM="min_power"

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
	# Set ALPM for all host adapters that support it
	set_alpm ${ALPM}

	# Enables USB autosuspend for all devices
	for i in /sys/bus/usb/devices/*/power/autosuspend; do echo 1 > $i; done

	# Enables multi core power savings for low wakeup systems
	[ -e /sys/devices/system/cpu/sched_mc_power_savings ] && echo 1 > /sys/devices/system/cpu/sched_mc_power_savings

	# Enable ondemand governor (best for powersaving)
	[ -e /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ] && echo ondemand > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

	# Enable AC97 audio power saving
	[ -e /sys/module/snd_ac97_codec/parameters/power_save ] && echo Y > /sys/module/snd_ac97_codec/parameters/power_save

	# Disable HAL polling of CDROMS
	for i in /dev/scd*; do hal-disable-polling --device $i; done

	# Enable power saving mode for Wi-Fi cards
	for i in /sys/bus/pci/devices/*/power_level ; do echo 5 > $i ; done

	return 0
}

stop() {
	set_alpm "max_performance"

	# Disables USB autosuspend for all devices
	for i in /sys/bus/usb/devices/*/power/autosuspend; do echo 0 > $i; done

	# Disables multi core power savings for low wakeup systems
	[ -e /sys/devices/system/cpu/sched_mc_power_savings ] && echo 0 > /sys/devices/system/cpu/sched_mc_power_savings

	# Enable ondemand governor (best for powersaving)
	[ -e /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ] && echo ondemand > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

	# Enable AC97 audio power saving
	[ -e /sys/module/snd_ac97_codec/parameters/power_save ] && echo Y > /sys/module/snd_ac97_codec/parameters/power_save

	# Enable HAL polling of CDROMS
	for i in /dev/scd*; do hal-disable-polling --enable-polling --device $i; done

	# Reset power saving mode for Wi-Fi cards
	for i in /sys/bus/pci/devices/*/power_level ; do echo 0 > $i ; done

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
