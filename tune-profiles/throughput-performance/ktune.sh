#!/bin/sh

. /etc/tune-profiles/functions

start() {
	set_cpu_governor performance
	set_transparent_hugepages always

	return 0
}

stop() {
	restore_cpu_governor
	restore_transparent_hugepages

	return 0
}

process $@
