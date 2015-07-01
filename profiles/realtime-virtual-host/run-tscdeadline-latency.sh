#!/bin/bash

QEMU=/usr/libexec/qemu-kvm

if [ ! -f /sys/module/kvm/parameters/lapic_timer_advance_ns ]; then
        echo "/sys/module/kvm/parameters/lapic_timer_advance_ns not found"
        exit 1
fi

dir=`mktemp -d`

for i in `seq 1000 500 7000`; do
	echo $i > /sys/module/kvm/parameters/lapic_timer_advance_ns
	chrt -f 1 taskset -c $1 $QEMU -enable-kvm -device pc-testdev \
		-device isa-debug-exit,iobase=0xf4,iosize=0x4 \
		-display none -serial stdio -device pci-testdev \
		-kernel /usr/share/qemu-kvm/tscdeadline_latency.flat  \
		-cpu host | grep latency | cut -f 2 -d ":" > $dir/out

	A=0
	while read l; do
		A=$(($A+$l))
	done < $dir/out

	lines=`wc -l $dir/out | cut -f 1 -d " "`; ans=$(($A/$lines));
	echo $i: $ans
done
