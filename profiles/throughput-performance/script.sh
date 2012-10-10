#!/bin/sh

. /usr/lib/tuned/functions

start() {
    set_elevator "/sys/block/{sd,cciss,dm-,vd}*/queue/scheduler" deadline
    enable_transparent_hugepages
    return 0
}

stop() {
    restore_elevator "/sys/block/{sd,cciss,dm-,vd}*/queue/scheduler"
    restore_transparent_hugepages
    return 0
}

process $@
