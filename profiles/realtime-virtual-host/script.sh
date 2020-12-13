#!/bin/bash

. /usr/lib/tuned/functions

start() {
    setup_kvm_mod_low_latency
    return 0
}

stop() {
    if [ "$1" = "full_rollback" ]; then
        teardown_kvm_mod_low_latency
    fi
    return "$?"
}

verify() {
    retval=0

    # set via /etc/modprobe.d/kvm.conf and /etc/modprobe.d/kvm.rt.tuned.conf
    if [ -f /sys/module/kvm/parameters/kvmclock_periodic_sync ]; then
        kps=$(cat /sys/module/kvm/parameters/kvmclock_periodic_sync)
        if [ "$kps" = "N" -o "$kps" = "0" ]; then
            echo "  kvmclock_periodic_sync:($kps): disabled: okay"
        else
            echo "  kvmclock_periodic_sync:($kps): enabled: expected N(0)"
            retval=1
        fi
    fi
    if [ -f /sys/module/kvm_intel/parameters/ple_gap ]; then
        ple_gap=$(cat /sys/module/kvm_intel/parameters/ple_gap)
        if [ $ple_gap -eq 0 ]; then
            echo "  ple_gap:($ple_gap): disabled: okay"
        else
            echo "  ple_gap:($ple_gap): enabled: expected 0"
            retval=1
        fi
    fi
    if [ -f /sys/module/kvm/parameters/nx_huge_pages ]; then
        kps=$(cat /sys/module/kvm/parameters/nx_huge_pages)
        if [ "$kps" = "N" -o "$kps" = "0" ]; then
            echo "  kvmclock_periodic_sync:($kps): disabled: okay"
        else
            echo "  kvmclock_periodic_sync:($kps): enabled: expected N(0)"
            retval=1
        fi
    fi
    return $retval
}

process $@
