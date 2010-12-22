#!/bin/sh

. /etc/tune-profiles/functions

start() {
	set_cpu_governor performance
	enable_transparent_hugepages

	return 0
}

stop() {
	restore_cpu_governor
	restore_transparent_hugepages

	return 0
}

process $@
