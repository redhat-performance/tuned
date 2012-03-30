#!/bin/sh

. /usr/lib/tuned/functions

start() {
    set_cpu_governor ondemand
    enable_snd_ac97_powersave
    set_hda_intel_powersave 10
    set_radeon_powersave auto
    return 0
}

stop() {
    restore_cpu_governor
    restore_snd_ac97_powersave
    restore_hda_intel_powersave
    restore_radeon_powersave
    return 0
}

process $@
