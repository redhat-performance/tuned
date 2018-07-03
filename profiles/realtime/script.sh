#!/bin/sh

. /usr/lib/tuned/functions

start() {
    return 0
}

stop() {
    return 0
}

verify() {
    tuna -c "$TUNED_isolated_cores" -P
    return "$?"
}

process $@
