#!/bin/sh

. /usr/lib/tuned/functions

start() {
    irqbalance_banned_cpus_setup "$TUNED_isolated_cpumask"
    return 0
}

stop() {
    irqbalance_banned_cpus_clear
    return 0
}

verify() {
    tuna -c "$TUNED_isolated_cores" -P
    return "$?"
}

process $@
