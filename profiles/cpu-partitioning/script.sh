#!/bin/sh

. /usr/lib/tuned/functions

start() {
    mkdir -p "${TUNED_tmpdir}/etc/systemd"
    mkdir -p "${TUNED_tmpdir}/usr/lib/dracut/hooks/pre-udev"
    cp /etc/systemd/system.conf "${TUNED_tmpdir}/etc/systemd/"
    cp 00-tuned-pre-udev.sh "${TUNED_tmpdir}/usr/lib/dracut/hooks/pre-udev/"
    python /usr/libexec/tuned/defirqaffinity.py "remove" "$TUNED_isolated_cores_expanded" &&
    tuna -c "$TUNED_isolated_cores_expanded" -i
    sed -i '/^IRQBALANCE_BANNED_CPUS=/d' /etc/sysconfig/irqbalance
    echo "IRQBALANCE_BANNED_CPUS=$TUNED_isolated_cpumask" >>/etc/sysconfig/irqbalance
    setup_kvm_mod_low_latency
    return "$?"
}

stop() {
    tuna -c "$TUNED_isolated_cores_expanded" -I &&
    python /usr/libexec/tuned/defirqaffinity.py "add" "$TUNED_isolated_cores_expanded"
    if [ "$1" = "full_rollback" ]
    then
        sed -i '/^IRQBALANCE_BANNED_CPUS=/d' /etc/sysconfig/irqbalance
        teardown_kvm_mod_low_latency
    fi
    return "$?"
}

verify() {
    python /usr/libexec/tuned/defirqaffinity.py "verify" "$TUNED_isolated_cores_expanded"
    return "$?"
}

process $@
