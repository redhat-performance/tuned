#!/bin/sh

# Oracle ktune script
# based on the throughput-performance profile

. /etc/tune-profiles/functions

start() {
	set_cpu_governor performance
	set_transparent_hugepages never

	return 0
}

stop() {
	restore_cpu_governor
	restore_transparent_hugepages

	return 0
}

process $@
