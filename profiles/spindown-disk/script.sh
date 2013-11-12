#!/bin/sh

. /usr/lib/tuned/functions

EXT_PARTITIONS=$(mount | grep -E "type ext(3|4)" | cut -d" " -f1)

start() {

    [ "$USB_AUTOSUSPEND" = 1 ] && enable_usb_autosuspend
    disable_bluetooth
    enable_wifi_powersave
    disable_logs_syncing

    remount_partitions commit=600,noatime $EXT_PARTITIONS
    sync

    return 0
}

stop() {

    [ "$USB_AUTOSUSPEND" = 1 ] && disable_usb_autosuspend
    enable_bluetooth
    disable_wifi_powersave
    restore_logs_syncing

    remount_partitions commit=5 $EXT_PARTITIONS

    return 0
}

process $@
