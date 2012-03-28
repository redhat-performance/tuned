#!/bin/sh

. /usr/lib/tuned/functions

start() {
    remount_all_no_rootboot_partitions nobarrier
    multiply_disk_readahead 4
    return 0
}

stop() {
    remount_all_no_rootboot_partitions barrier
    multiply_disk_readahead 0.25
    return 0
}

process $@
