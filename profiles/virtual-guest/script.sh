#!/bin/sh

. /usr/lib/tuned/functions

start() {
    remount_all_no_rootboot_partitions nobarrier
    return 0
}

stop() {
    remount_all_no_rootboot_partitions barrier
    return 0
}

process $@
