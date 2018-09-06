#!/bin/sh

. /usr/lib/tuned/functions

start() {
    systemctl start rt-entsk
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
