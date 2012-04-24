#!/bin/sh

. /usr/lib/tuned/functions

start() {
    set_elevator "/sys/block/{sd,cciss,dm-,vd}*/queue/scheduler" deadline
    set_cpu_governor performance

    return 0
}

stop() {
    restore_elevator "/sys/block/{sd,cciss,dm-,vd}*/queue/scheduler"
    restore_cpu_governor

    return 0
}

process $@
