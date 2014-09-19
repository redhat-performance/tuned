#!/bin/sh

. /etc/tune-profiles/functions

start() {
	set_cpu_governor performance
	/usr/libexec/tuned/pmqos-static.py cpu_dma_latency=1
	multiply_disk_readahead 4
	ethtool -K eth0 lro off
	set_transparent_hugepages never
	return 0
}

stop() {
	restore_cpu_governor
	/usr/libexec/tuned/pmqos-static.py disable
	restore_transparent_hugepages
	restore_disk_readahead
	ethtool -K eth0 lro on
	return 0
}

process $@
