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
    dir=`mktemp -d`

    for i in `seq 1000 500 7000`; do
        echo $i > $KVM_LAPIC_FILE
        chrt -f 1 taskset -c $1 $QEMU -enable-kvm -device pc-testdev \
            -device isa-debug-exit,iobase=0xf4,iosize=0x4 \
            -display none -serial stdio -device pci-testdev \
            -kernel "$TSCDEADLINE_LATENCY"  \
            -cpu host | grep latency | cut -f 2 -d ":" > $dir/out

	if [ ! -f $dir/out ]; then
	    die running $TSCDEADLINE_LATENCY failed
	fi

	tmp=$(wc -l $dir/out | awk '{ print $1 }')
	if [ $tmp -eq 0 ]; then
	    die running $TSCDEADLINE_LATENCY failed
	fi

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
    setup_kvm_mod_low_latency

    disable_ksm

    # If CPU model has changed, clean the cache
    if [ -f $CACHE_CPU_FILE ]; then
        curmodel=`cat /proc/cpuinfo | grep "model name" | cut -f 2 -d ":" | uniq`
	if [ -z "$curmodel" ]; then
	    die failed to read CPU model
	fi

        genmodel=`cat $CACHE_CPU_FILE`

        if [ "$curmodel" != "$genmodel" ]; then
            rm -f $CACHE_VALUE_FILE
            rm -f $CACHE_CPU_FILE
        fi
    fi

    # If the cache is empty, find the best lapic_timer_advance_ns value
    # and cache it

    if [ ! -f $KVM_LAPIC_FILE ]; then
	die $KVM_LAPIC_FILE not found
    fi

    if [ ! -f $CACHE_VALUE_FILE ]; then
        if [ -f "$TSCDEADLINE_LATENCY" ]; then
             tempdir=`mktemp -d`
             isolatedcpu=`echo "$TUNED_isolated_cores_expanded" | cut -f 1 -d ","`
             run_tsc_deadline_latency $isolatedcpu > $tempdir/lat.out
             if ! ./find-lapictscdeadline-optimal.sh $tempdir/lat.out > $tempdir/opt.out; then
		die could not find optimal latency
	     fi
             echo `cat $tempdir/opt.out | cut -f 2 -d ":"` > $CACHE_VALUE_FILE
             curmodel=`cat /proc/cpuinfo | grep "model name" | cut -f 2 -d ":" | uniq`
             echo "$curmodel" > $CACHE_CPU_FILE
        fi
    fi

    if [ -f $CACHE_VALUE_FILE ]; then
        echo `cat $CACHE_VALUE_FILE` > $KVM_LAPIC_FILE
    fi

    return 0
}

stop() {
    [ "$1" = "full_rollback" ] && teardown_kvm_mod_low_latency
    enable_ksm
    return "$?"
}

verify() {
    if [ -f /sys/module/kvm/parameters/kvmclock_periodic_sync ]; then
        test "$(cat /sys/module/kvm/parameters/kvmclock_periodic_sync)" = 0
        retval=$?
    fi
    if [ $retval -eq 0 -a -f /sys/module/kvm_intel/parameters/ple_gap ]; then
        test "$(cat /sys/module/kvm_intel/parameters/ple_gap)" = 0
        retval=$?
    fi
    return $retval
}

process $@
