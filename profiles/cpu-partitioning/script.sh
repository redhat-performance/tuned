#!/bin/sh

. /usr/lib/tuned/functions

no_balance_cpus_file=$STORAGE/no-balance-cpus.txt

change_sd_balance_bit()
{
    local set_bit=$1
    local flags_cur=
    local file=
    local cpu=

    for cpu in $(cat $no_balance_cpus_file); do
        for file in $(find /proc/sys/kernel/sched_domain/cpu$cpu -name flags -print); do
            flags_cur=$(cat $file)
            if [ $set_bit -eq 1 ]; then
                flags_cur=$((flags_cur | 0x1))
            else
                flags_cur=$((flags_cur & 0xfffe))
            fi
            echo $flags_cur > $file
        done
    done
}

disable_balance_domains()
{
    change_sd_balance_bit 0
}

enable_balance_domains()
{
    change_sd_balance_bit 1
}

start() {
    mkdir -p "${TUNED_tmpdir}/etc/systemd"
    mkdir -p "${TUNED_tmpdir}/usr/lib/dracut/hooks/pre-udev"
    cp /etc/systemd/system.conf "${TUNED_tmpdir}/etc/systemd/"
    cp 00-tuned-pre-udev.sh "${TUNED_tmpdir}/usr/lib/dracut/hooks/pre-udev/"
    setup_kvm_mod_low_latency
    disable_ksm

    echo "$TUNED_no_balance_cores_expanded" | sed 's/,/ /g' > $no_balance_cpus_file
    disable_balance_domains
    return "$?"
}

stop() {
    if [ "$1" = "full_rollback" ]
    then
        teardown_kvm_mod_low_latency
        enable_ksm
    fi
    enable_balance_domains
    return "$?"
}

process $@
