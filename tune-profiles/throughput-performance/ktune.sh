#!/bin/sh

. /etc/tune-profiles/functions

start() {
	set_cpu_governor performance
	enable_transparent_hugepages
	/usr/libexec/tuned/pmqos-static.py cpu_dma_latency=0

	return 0
}

stop() {
	restore_cpu_governor
	restore_transparent_hugepages
	/usr/libexec/tuned/pmqos-static.py disable

	return 0
}

process $@
