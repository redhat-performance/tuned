#!/bin/sh

. /usr/lib/tuned/functions

start() {
    if [ -z "$TUNED_isolated_cores" ]; then
      echo "no isolated cores set, realtime profile not correctly activated" >&2
      exit 1
    fi

    # move threads off the selected cpu cores
    tuna -c "$TUNED_isolated_cores" -i

    return "$?"
}

stop() {
    return 0
}

verify() {
    tuna -c "$TUNED_isolated_cores" -P
    return "$?"
}

process $@
