#!/bin/sh

VAR_SUBSYS_KTUNE="/var/lock/subsys/ktune"

CPUSPEED_SAVE_FILE="/var/run/tuned/ktune-cpuspeed.save"
CPUSPEED_ORIG_GOV="/var/run/tuned/ktune-cpuspeed-governor-%s.save"
CPUSPEED_STARTED="/var/run/tuned/ktune-cpuspeed-started"
CPUSPEED_CFG="/etc/sysconfig/cpuspeed"
CPUSPEED_INIT="/etc/init.d/cpuspeed"
CPUS="$(ls -d1 /sys/devices/system/cpu/cpu* | sed 's;^.*/;;' |  grep "cpu[0-9]\+")"

THP_ENABLE="/sys/kernel/mm/redhat_transparent_hugepage/enabled"
THP_SAVE="/var/run/tuned/ktune-thp.save"

start() {
	# Enable performance CPU governor (prefer cpuspeed), if freq scaling is supported
	if [ -e $CPUSPEED_INIT ]; then
		if [ ! -e $CPUSPEED_SAVE_FILE -a -e $CPUSPEED_CFG ]; then
			cp -p $CPUSPEED_CFG $CPUSPEED_SAVE_FILE
			sed -e 's/^GOVERNOR=.*/GOVERNOR=performance/g' $CPUSPEED_SAVE_FILE > $CPUSPEED_CFG
		fi

		service cpuspeed status >/dev/null 2>&1
		[ $? -eq 3 ] && touch $CPUSPEED_STARTED || rm -f $CPUSPEED_STARTED

		service cpuspeed restart >/dev/null 2>&1
	elif [ -e /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
		echo >/dev/stderr
		echo "Suggestion: install 'cpuspeed' package to get best performance and latency." >/dev/stderr
		echo "Falling back to 'performance' scaling governor for all CPUs." >/dev/stderr
		echo >/dev/stderr

		for cpu in $CPUS; do
			gov_file=/sys/devices/system/cpu/$cpu/cpufreq/scaling_governor
			save_file=$(printf $CPUSPEED_ORIG_GOV $cpu)
			rm -f $save_file
			if [ -e $gov_file ]; then
				cat $gov_file > $save_file
				echo performance > $gov_file
			fi
		done
	fi

	# Make sure transparent hugepages are enabled (if supported)
	if [ -e $THP_ENABLE ]; then
		cut -f2 -d'[' $THP_ENABLE  | cut -f1 -d']' > $THP_SAVE
		(echo always > $THP_ENABLE) > /dev/null 2>&1
	fi

	# Find non-root and non-boot partitions, disable barriers on them
	rootvol=$(df -h / | grep "^/dev" | awk '{print $1}')
	bootvol=$(df -h /boot | grep "^/dev" | awk '{print $1}')
	volumes=$(df -hl --exclude=tmpfs | grep "^/dev" | awk '{print $1}')

	nobarriervols=$(echo "$volumes" | grep -v $rootvol | grep -v $bootvol)
	for vol in $nobarriervols
	do
		/bin/mount -o remount,nobarrier $vol > /dev/null 2>&1
	done

	# Increase the readahead value on all volumes
	readaheadvols=$(ls /sys/block/{sd,cciss}*/queue/read_ahead_kb 2>/dev/null)
	for d in $readaheadvols
	do
		(echo 512 > $d) > /dev/null 2>&1
	done

	return 0
}

stop() {
	# Re-enable previous CPU governor
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
	elif [ -e /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
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

	# Restore transparent hugepages setting
	if [ -e $THP_SAVE ]; then
		(echo $(cat $THP_SAVE) > $THP_ENABLE) > /dev/null 2>&1
		rm -f $THP_SAVE
	fi

	# Find non-root and non-boot partitions, re-enable barriers
	rootvol=$(df -h / | grep "^/dev" | awk '{print $1}')
	bootvol=$(df -h /boot | grep "^/dev" | awk '{print $1}')
	volumes=$(df -hl --exclude=tmpfs | grep "^/dev" | awk '{print $1}')

	nobarriervols=$(echo "$volumes" | grep -v $rootvol | grep -v $bootvol)
	for vol in $nobarriervols
	do
		/bin/mount -o remount,barrier $vol > /dev/null 2>&1
	done

	# Reset default readahead value on all volumes
	readaheadvols=$(ls /sys/block/{sd,cciss}*/queue/read_ahead_kb 2>/dev/null)
	for d in $readaheadvols
	do
		(echo 128 > $d) > /dev/null 2>&1
	done

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
