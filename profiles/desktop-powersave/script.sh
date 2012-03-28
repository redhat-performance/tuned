#!/bin/sh

. /usr/lib/tuned/functions

start() {
    set_radeon_powersave auto
    return 0
}

stop() {
    restore_radeon_powersave
    return 0
}
