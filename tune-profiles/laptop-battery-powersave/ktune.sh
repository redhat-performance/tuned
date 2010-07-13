#!/bin/sh

VAR_SUBSYS_KTUNE="/var/lock/subsys/ktune"

CPUSPEED_SAVE_FILE="/var/run/tuned/ktune-cpuspeed.save"
CPUSPEED_ORIG_GOV="/var/run/tuned/ktune-cpuspeed-governor-%s.save"
CPUSPEED_STARTED="/var/run/tuned/ktune-cpuspeed-started"
CPUSPEED_CFG="/etc/sysconfig/cpuspeed"
CPUSPEED_INIT="/etc/init.d/cpuspeed"
CPUS="$(ls -d1 /sys/devices/system/cpu/cpu* | sed 's;^.*/;;' |  grep "cpu[0-9]\+")"

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
	#for i in /sys/bus/usb/devices/*/power/autosuspend; do echo 1 > $i; done > /dev/null 2>&1

	# Enables multi core power savings for low wakeup systems
	[ -e /sys/devices/system/cpu/sched_mc_power_savings ] && echo 1 > /sys/devices/system/cpu/sched_mc_power_savings

	# Enable ondemand CPU governor (prefer cpuspeed)
	if [ -e $CPUSPEED_INIT ]; then
		if [ ! -e $CPUSPEED_SAVE_FILE -a -e $CPUSPEED_CFG ]; then
			cp -p $CPUSPEED_CFG $CPUSPEED_SAVE_FILE
			sed -e 's/^GOVERNOR=.*/GOVERNOR=ondemand/g' $CPUSPEED_SAVE_FILE > $CPUSPEED_CFG
		fi

		service cpuspeed status >/dev/null 2>&1
		[ $? -eq 3 ] && touch $CPUSPEED_STARTED || rm -f $CPUSPEED_STARTED

		service cpuspeed restart >/dev/null 2>&1
	else
		echo >/dev/stderr
		echo "Suggestion: install 'cpuspeed' package to get better powersaving results." >/dev/stderr
		echo "Falling back to 'ondemand' scaling governor for all CPUs." >/dev/stderr
		echo >/dev/stderr

		for cpu in $CPUS; do
			gov_file=/sys/devices/system/cpu/$cpu/cpufreq/scaling_governor
			save_file=$(printf $CPUSPEED_ORIG_GOV $cpu)
			rm -f $save_file
			if [ -e $gov_file ]; then
				cat $gov_file > $save_file
				echo ondemand > $gov_file
			fi
		done
	fi

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
	#for i in /sys/bus/usb/devices/*/power/autosuspend; do echo 0 > $i; done > /dev/null 2>&1

	# Disables multi core power savings for low wakeup systems
	[ -e /sys/devices/system/cpu/sched_mc_power_savings ] && echo 0 > /sys/devices/system/cpu/sched_mc_power_savings

	# Revert previous CPU governor
	if [ -e $CPUSPEED_INIT ]; then
		if [ -e $CPUSPEED_SAVE_FILE ]; then
			cp -fp $CPUSPEED_SAVE_FILE $CPUSPEED_CFG
			rm -f $CPUSPEED_SAVE_FILE
		fi

		if [ -e $CPUSPEED_STARTED ]; then
			rm -f $CPUSPEED_STARTED
			service cpuspeed stop >/dev/null 2>&1
		else
			service cpuspeed restart >/dev/null 2>&1
		fi
	else
		for cpu in $CPUS; do
			cpufreq_dir=/sys/devices/system/cpu/$cpu/cpufreq
			save_file=$(printf $CPUSPEED_ORIG_GOV $cpu)

			if [ -e $cpufreq_dir/scaling_governor ]; then
				if [ -e $save_file ]; then
					cat $save_file > $cpufreq_dir/scaling_governor
					rm -f $save_file
				else
					echo userspace > $cpufreq_dir/scaling_governor
					cat $cpufreq_dir/cpuinfo_max_freq > $cpufreq_dir/scaling_setspeed
				fi
			fi
		done
	fi

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
