#!/bin/bash

. /usr/lib/tuned/functions

start() {
    DRACUT_VER=`dracut --version | sed 's/^.* \([0-9]\+\).*/\1/'`
    echo "$DRACUT_VER" | grep -q '^[[:digit:]]\+$' || DRACUT_VER="0"
    # https://issues.redhat.com/browse/RHEL-119889
    if [ "$DRACUT_VER" -gt "102" ]
    then
      DRACUT_HOOK_DIR="/var/lib/dracut/hooks/pre-udev"
    else
      DRACUT_HOOK_DIR="/usr/lib/dracut/hooks/pre-udev"
    fi
    mkdir -p "${TUNED_tmpdir}/etc/systemd"
    mkdir -p "${TUNED_tmpdir}${DRACUT_HOOK_DIR}"
    cp /etc/systemd/system.conf "${TUNED_tmpdir}/etc/systemd/"
    cp 00-tuned-pre-udev.sh "${TUNED_tmpdir}${DRACUT_HOOK_DIR}"
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
