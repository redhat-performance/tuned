#!/bin/sh

. /usr/lib/tuned/functions

start() {
    enable_wifi_powersave
    return 0
}

stop() {
    disable_wifi_powersave
    return 0
}

process $@
