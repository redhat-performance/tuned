#!/bin/bash

. /usr/lib/tuned/functions

start() {
    return 0
}

stop() {
    return 0
}

verify() {
    retval=0
    if [ "$TUNED_isolated_cores" ]; then
        tuna -c "$TUNED_isolated_cores" -P > /dev/null 2>&1
        retval=$?
    fi
    return $retval
}

process $@
