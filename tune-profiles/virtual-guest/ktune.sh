#!/bin/sh

. /etc/tune-profiles/functions

start() {
	set_cpu_governor performance
	enable_transparent_hugepages

	# Find non-root and non-boot partitions, disable barriers on them
	rootvol=$(df -h / | grep "^/dev" | awk '{print $1}')
	bootvol=$(df -h /boot | grep "^/dev" | awk '{print $1}')
	volumes=$(df -hl --exclude=tmpfs | grep "^/dev" | awk '{print $1}')

	nobarriervols=$(echo "$volumes" | grep -v $rootvol | grep -v $bootvol)
	remount_partitions nobarrier $nobarriervols

	multiply_disk_readahead 4

	return 0
}

stop() {
	restore_cpu_governor
	restore_transparent_hugepages

	# Find non-root and non-boot partitions, re-enable barriers
	rootvol=$(df -h / | grep "^/dev" | awk '{print $1}')
	bootvol=$(df -h /boot | grep "^/dev" | awk '{print $1}')
	volumes=$(df -hl --exclude=tmpfs | grep "^/dev" | awk '{print $1}')

	nobarriervols=$(echo "$volumes" | grep -v $rootvol | grep -v $bootvol)
	remount_partitions barrier $nobarriervols

	multiply_disk_readahead 0.25

	return 0
}

process $@
