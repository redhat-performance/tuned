#!/bin/sh

. /usr/lib/tuned/functions

start() {
    set_elevator "/sys/block/{sd,cciss,dm-,vd}*/queue/scheduler" deadline

    return 0
}

stop() {
    restore_elevator "/sys/block/{sd,cciss,dm-,vd}*/queue/scheduler"

    return 0
}

process $@
