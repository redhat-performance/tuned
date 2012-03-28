#!/bin/sh

. /usr/lib/tuned/functions

start() {
    set_elevator "/sys/block/{sd,cciss,dm-}*/queue/scheduler" deadline
    set_cpu_governor performance
    enable_transparent_hugepages
    remount_all_no_rootboot_partitions nobarrier
    multiply_disk_readahead 4
    return 0
}

stop() {
    restore_elevator "/sys/block/{sd,cciss,dm-}*/queue/scheduler"
    restore_cpu_governor
    restore_transparent_hugepages
    remount_all_no_rootboot_partitions barrier
    multiply_disk_readahead 0.25
    return 0
}

process $@
