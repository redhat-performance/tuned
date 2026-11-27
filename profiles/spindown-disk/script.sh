#!/bin/bash

. /usr/lib/tuned/functions

# handle special chars in mount names by escaping (-r) and unescaping (%b)
mapfile -t EXT_MOUNTS < <(findmnt -rn -t ext3,ext4 -o TARGET)
for i in "${!EXT_MOUNTS[@]}"; do
    printf -v "EXT_MOUNTS[$i]" "%b" "${EXT_MOUNTS[$i]}"
done

start() {

    [ "$USB_AUTOSUSPEND" = 1 ] && enable_usb_autosuspend
    disable_bluetooth
    enable_wifi_powersave
    disable_logs_syncing

    remount_partitions commit=600,noatime "${EXT_MOUNTS[@]}"
    sync

    return 0
}

stop() {

    [ "$USB_AUTOSUSPEND" = 1 ] && disable_usb_autosuspend
    enable_bluetooth
    disable_wifi_powersave
    restore_logs_syncing

    remount_partitions commit=5 "${EXT_MOUNTS[@]}"

    return 0
}

process $@
