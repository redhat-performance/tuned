#!/bin/sh

. /usr/lib/tuned/functions

KTIMER_LOCKLESS_FILE=/sys/kernel/ktimer_lockless_check

start() {
    if [ -f $KTIMER_LOCKLESS_FILE ]; then
        echo 1 > $KTIMER_LOCKLESS_FILE
    fi
    return "$?"
}

stop() {
    return 0
}

verify() {
    return "$?"
}

process $@
