#!/bin/sh

. /usr/lib/tuned/functions

KTIMER_LOCKLESS_FILE=/sys/kernel/ktimer_lockless_check

start() {
    systemctl start rt-entsk
    if [ -f $KTIMER_LOCKLESS_FILE ]; then
        echo 1 > $KTIMER_LOCKLESS_FILE
    fi
    return "$?"
}

stop() {
    systemctl stop rt-entsk
    return "$?"
}

verify() {
    return "$?"
}

process $@
