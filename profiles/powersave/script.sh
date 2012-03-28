#!/bin/sh

. /usr/lib/tuned/functions

start() {
    [ "$USB_AUTOSUSPEND" = 1 ] && enable_usb_autosuspend
    set_disk_alpm min_power
    enable_cpu_multicore_powersave
    set_cpu_governor ondemand
    enable_snd_ac97_powersave
    set_hda_intel_powersave 10
    enable_wifi_powersave
    set_radeon_powersave auto
    return 0
}

stop() {
    [ "$USB_AUTOSUSPEND" = 1 ] && disable_usb_autosuspend
    set_disk_alpm max_performance
    disable_cpu_multicore_powersave
    restore_cpu_governor
    restore_snd_ac97_powersave
    restore_hda_intel_powersave
    disable_wifi_powersave
    restore_radeon_powersave
    return 0
}

process $@
