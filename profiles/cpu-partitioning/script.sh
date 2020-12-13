#!/bin/bash

. /usr/lib/tuned/functions

start() {
    mkdir -p "${TUNED_tmpdir}/etc/systemd"
    mkdir -p "${TUNED_tmpdir}/usr/lib/dracut/hooks/pre-udev"
    cp /etc/systemd/system.conf "${TUNED_tmpdir}/etc/systemd/"
    cp 00-tuned-pre-udev.sh "${TUNED_tmpdir}/usr/lib/dracut/hooks/pre-udev/"
    setup_kvm_mod_low_latency
    disable_ksm
    return "$?"
}

stop() {
    if [ "$1" = "full_rollback" ]
    then
        teardown_kvm_mod_low_latency
        enable_ksm
    fi
    return "$?"
}

process $@
