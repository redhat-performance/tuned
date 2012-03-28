#!/bin/sh

. /usr/lib/tuned/functions

start() {
    set_elevator "/sys/block/{sd,cciss,dm-,vd}*/queue/scheduler" deadline
    set_cpu_governor performance
    /usr/libexec/tuned/pmqos-static.py cpu_dma_latency=0

    return 0
}

stop() {
    restore_elevator "/sys/block/{sd,cciss,dm-,vd}*/queue/scheduler"
    restore_cpu_governor
    /usr/libexec/tuned/pmqos-static.py disable

    return 0
}

process $@
