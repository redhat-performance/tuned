#!/bin/sh

. /etc/tune-profiles/functions

start() {
	set_cpu_governor performance
	set_transparent_hugepages always
	disable_disk_barriers
	multiply_disk_readahead 4

	return 0
}

stop() {
	restore_cpu_governor
	restore_transparent_hugepages
	enable_disk_barriers
	multiply_disk_readahead 0.25

	return 0
}

process $@
