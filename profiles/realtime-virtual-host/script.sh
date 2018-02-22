#!/bin/sh

. /usr/lib/tuned/functions

CACHE_VALUE_FILE=./lapic_timer_adv_ns
CACHE_CPU_FILE=./lapic_timer_adv_ns.cpumodel
KVM_LAPIC_FILE=/sys/module/kvm/parameters/lapic_timer_advance_ns
QEMU=$(type -P qemu-kvm || echo /usr/libexec/qemu-kvm)
TSCDEADLINE_LATENCY="/usr/share/qemu-kvm/tscdeadline_latency.flat"
if [ ! -f "$TSCDEADLINE_LATENCY" ]; then
    TSCDEADLINE_LATENCY="/usr/share/tuned/tscdeadline_latency.flat"
fi

run_tsc_deadline_latency()
{
    if [ ! -f $KVM_LAPIC_FILE ]; then
        echo "$KVM_LAPIC_FILE not found"
        return 1
    fi

    dir=`mktemp -d`

    for i in `seq 1000 500 7000`; do
        echo $i > $KVM_LAPIC_FILE
        chrt -f 1 taskset -c $1 $QEMU -enable-kvm -device pc-testdev \
            -device isa-debug-exit,iobase=0xf4,iosize=0x4 \
            -display none -serial stdio -device pci-testdev \
            -kernel "$TSCDEADLINE_LATENCY"  \
            -cpu host | grep latency | cut -f 2 -d ":" > $dir/out

        A=0
        while read l; do
            A=$(($A+$l))
        done < $dir/out

        lines=`wc -l $dir/out | cut -f 1 -d " "`
        ans=$(($A/$lines))
        echo $i: $ans
    done
}

start() {
    python /usr/libexec/tuned/defirqaffinity.py "remove" "$TUNED_isolated_cores_expanded" &&
    retval = "$?"

    if [ ! $retval -eq 0 ]; then
        return $retval
    fi

    setup_kvm_mod_low_latency

    if [ -f $CACHE_CPU_FILE ]; then
        curmodel=`cat /proc/cpuinfo | grep "model name" | cut -f 2 -d ":" | uniq`
        genmodel=`cat $CACHE_CPU_FILE`

        if [ "$curmodel" != "$genmodel" ]; then
            rm -f $CACHE_VALUE_FILE
            rm -f $CACHE_CPU_FILE
        fi
    fi


    if [ -f $KVM_LAPIC_FILE -a ! -f $CACHE_VALUE_FILE ]; then
        if [ -f "$TSCDEADLINE_LATENCY" ]; then
             tempdir=`mktemp -d`
             isolatedcpu=`echo "$TUNED_isolated_cores_expanded" | cut -f 1 -d ","`
             run_tsc_deadline_latency $isolatedcpu > $tempdir/lat.out
             sh ./find-lapictscdeadline-optimal.sh $tempdir/lat.out > $tempdir/opt.out
             if [ $? -eq 0 ]; then
                  echo `cat $tempdir/opt.out | cut -f 2 -d ":"` > $CACHE_VALUE_FILE
                  curmodel=`cat /proc/cpuinfo | grep "model name" | cut -f 2 -d ":" | uniq`
                  echo "$curmodel" > $CACHE_CPU_FILE
             fi
        fi
    fi
    if [ -f $KVM_LAPIC_FILE -a -f $CACHE_VALUE_FILE ]; then
        echo `cat $CACHE_VALUE_FILE` > $KVM_LAPIC_FILE
    fi

    disable_ksm

    return $retval
}

stop() {
    [ "$1" = "full_rollback" ] && teardown_kvm_mod_low_latency
    python /usr/libexec/tuned/defirqaffinity.py "add" "$TUNED_isolated_cores_expanded"
    enable_ksm
    return "$?"
}

verify() {
    python /usr/libexec/tuned/defirqaffinity.py "verify" "$TUNED_isolated_cores_expanded"
    retval = "$?"
    if [ $retval -eq 0 -a -f /sys/module/kvm/parameters/kvmclock_periodic_sync ]; then
        retval = `cat /sys/module/kvm/parameters/kvmclock_periodic_sync`
    fi
    if [ $retval -eq 0 -a -f /sys/module/kvm_intel/parameters/ple_gap ]; then
        retval = `cat /sys/module/kvm_intel/parameters/ple_gap`
    fi
    return $retval
}

process $@
