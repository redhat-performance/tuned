#!/bin/sh

. /etc/tune-profiles/functions

EXT_PARTITIONS=$(mount | grep -E "type ext(3|4)" | cut -d" " -f1)

start() {
	set_disk_alpm medium_power
	set_disk_apm 128
	set_disk_spindown 6

	enable_usb_autosuspend
	disable_cd_polling
	disable_bluetooth
	enable_wifi_powersave
	disable_logs_syncing

	remount_partitions commit=600,noatime $EXT_PARTITIONS
	find /etc/ &> /dev/null
	sync

	return 0
}

stop() {
	set_disk_alpm max_power
	set_disk_apm 255
	set_disk_spindown 0

	disable_usb_autosuspend
	enable_bluetooth
	disable_wifi_powersave
	restore_logs_syncing

	remount_partitions commit=5 $EXT_PARTITIONS

	return 0
}

process $@
