#!/bin/sh

. /etc/tune-profiles/functions

start() {
	set_cpu_governor performance
	/usr/libexec/tuned/pmqos-static.py cpu_dma_latency=0

	return 0
}

stop() {
	restore_cpu_governor
	/usr/libexec/tuned/pmqos-static.py disable

	return 0
}

process $@
