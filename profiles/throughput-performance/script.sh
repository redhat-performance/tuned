#!/bin/sh

. /usr/lib/tuned/functions

start() {
    set_elevator "/sys/block/{sd,cciss,dm-,vd}*/queue/scheduler" deadline
    set_cpu_governor performance
    enable_transparent_hugepages
    return 0
}

stop() {
    restore_elevator "/sys/block/{sd,cciss,dm-,vd}*/queue/scheduler"
    restore_cpu_governor
    restore_transparent_hugepages
    return 0
}
