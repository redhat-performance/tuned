#!/bin/sh

. /usr/lib/tuned/functions

start() {
    python /usr/libexec/tuned/defirqaffinity.py "remove" "$TUNED_isolated_cores_expanded" &&
    return "$?"
}

stop() {
    python /usr/libexec/tuned/defirqaffinity.py "add" "$TUNED_isolated_cores_expanded"
    return "$?"
}

verify() {
    python /usr/libexec/tuned/defirqaffinity.py "verify" "$TUNED_isolated_cores_expanded"
    return "$?"
}

process $@
