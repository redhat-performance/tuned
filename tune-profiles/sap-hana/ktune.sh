#!/bin/sh

# RHEL for SAP HANA ktune script
# based on the enterprise-storage profile

. /etc/tune-profiles/functions

start() {
	set_cpu_governor performance
	/usr/libexec/tuned/pmqos-static.py cpu_dma_latency=1
	set_transparent_hugepages never
	multiply_disk_readahead 4

	return 0
}

stop() {
	restore_cpu_governor
	/usr/libexec/tuned/pmqos-static.py disable
	restore_transparent_hugepages
	restore_disk_readahead

	return 0
}

process $@
