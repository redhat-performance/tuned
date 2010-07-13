#!/bin/sh

VAR_SUBSYS_KTUNE="/var/lock/subsys/ktune"

CPUSPEED_SAVE_FILE="/var/run/tuned/ktune-cpuspeed.save"
CPUSPEED_ORIG_GOV="/var/run/tuned/ktune-cpuspeed-governor.save"
CPUSPEED_CFG="/etc/sysconfig/cpuspeed"
CPUSPEED_INIT="/etc/init.d/cpuspeed"
CPUS="/sys/devices/system/cpu*/cpufreq"

THP_ENABLE="/sys/kernel/mm/redhat_transparent_hugepage/enabled"
THP_SAVE="/var/run/tuned/ktune-thp.save"

start() {
	# Save currently enabled governor and/or cpuspeed config
	cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor > $CPUSPEED_ORIG_GOV
	if [ ! -e $CPUSPEED_SAVE_FILE -a -e $CPUSPEED_CFG ]; then
		cp -p $CPUSPEED_CFG $CPUSPEED_SAVE_FILE
		sed -e 's/^GOVERNOR=.*/GOVERNOR=performance/g' $CPUSPEED_SAVE_FILE > $CPUSPEED_CFG
	fi

	# Enable performance governor (best for maximum i/o throughput in most cases)
	if [ -e $CPUSPEED_INIT ]; then
		/sbin/service cpuspeed restart > /dev/null 2>&1
	else
		for cpu in $CPUS; do
			echo performance > $cpu/scaling_governor
		done
	fi

	# Make sure transparent hugepages are enabled
	cut -f2 -d'[' $THP_ENABLE  | cut -f1 -d']' > $THP_SAVE
	(echo always > $THP_ENABLE) > /dev/null 2>&1

	return 0
}

stop() {
	# Restore previous cpuspeed config
	if [ -e $CPUSPEED_SAVE_FILE ]; then
		cp -fp $CPUSPEED_SAVE_FILE $CPUSPEED_CFG
		rm -f $CPUSPEED_SAVE_FILE
	fi

	# Re-enable previous governor
	if [ -e $CPUSPEED_INIT ]; then
		/sbin/service cpuspeed restart > /dev/null 2>&1
	elif [ -e $CPUSPEED_ORIG_GOV ]; then
		for cpu in $CPUS; do
			echo $(cat $CPUSPEED_ORIG_GOV) > $cpu/scaling_governor
		done
	else
		for cpu in $CPUS; do
			echo userspace > $cpu/scaling_governor
			cat $cpu/cpuinfo_max_freq > $cpu/scaling_setspeed
		done
	fi
	if [ -e $CPUSPEED_ORIG_GOV ]; then
		rm -f $CPUSPEED_ORIG_GOV
	fi

	# Restore transparent hugepages setting
	if [ -e $THP_SAVE ]; then
		(echo $(cat $THP_SAVE) > $THP_ENABLE) > /dev/null 2>&1
		rm -f $THP_SAVE
	fi

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
