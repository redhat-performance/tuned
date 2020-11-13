#!/bin/sh

. /usr/lib/tuned/functions

KTIMER_LOCKLESS_FILE=/sys/kernel/ktimer_lockless_check

start() {
    setup_kvm_mod_low_latency

    disable_ksm

    if [ -f $KTIMER_LOCKLESS_FILE ]; then
        echo 1 > $KTIMER_LOCKLESS_FILE
    fi

    return 0
}

stop() {
    if [ "$1" = "full_rollback" ]; then
        teardown_kvm_mod_low_latency
        enable_ksm
    fi
    return "$?"
}

verify() {
    if [ -f /sys/module/kvm/parameters/kvmclock_periodic_sync ]; then
        test "$(cat /sys/module/kvm/parameters/kvmclock_periodic_sync)" = 0
        retval=$?
    fi
    if [ $retval -eq 0 -a -f /sys/module/kvm_intel/parameters/ple_gap ]; then
        test "$(cat /sys/module/kvm_intel/parameters/ple_gap)" = 0
        retval=$?
    fi
    return $retval
}

process $@
