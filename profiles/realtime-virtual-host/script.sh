#!/bin/sh

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
    # set via /etc/modprobe.d/kvm.conf and /etc/modprobe.d/kvm.rt.tuned.conf
    if [ -f /sys/module/kvm/parameters/kvmclock_periodic_sync ]; then
        test "$(cat /sys/module/kvm/parameters/kvmclock_periodic_sync)" = "Y"
        retval=$?
        if [ $retval -eq 0 ]; then
            echo "  kvmclock_periodic_sync:(Y): enabled: expected N"
        else
            echo "  kvmclock_periodic_sync:(N): disabled: okay"
        fi
    fi
    if [ -f /sys/module/kvm_intel/parameters/ple_gap ]; then
        test $(cat /sys/module/kvm_intel/parameters/ple_gap) -eq 0
        retval=$?
        ple_gap=$(cat /sys/module/kvm_intel/parameters/ple_gap)
        if [ $retval -eq 0 ]; then
            echo "  ple_gap:($ple_gap): disabled: okay"
        else
            echo "  ple_gap:($ple_gap): enabled: expected 0"
        fi
    fi

    return $retval
}


process $@
