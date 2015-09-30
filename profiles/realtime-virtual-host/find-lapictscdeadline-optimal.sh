#!/bin/bash

: ${1?"Usage: $0 latency-file"}

lines=`wc -l $1 | cut -f 1 -d " "`
in_range=0
prev_value=1
for i in `seq 1 $lines`; do
	a=`awk "NR==$i" $1 | cut -f 2 -d ":"`
	value=$(($a*100/$prev_value))
	if [ $value -ge 98 -a $value -le 102 ]; then
		in_range=$(($in_range + 1))
	else
		in_range=0
	fi
	if [ $in_range -ge 2 ]; then
		echo -n "optimal value for lapic_timer_advance_ns is: "
		awk "NR==$(($i - 1))" $1 | cut -f 1 -d ":"
		exit 0
	fi
	prev_value=$a
done
# if still decreasing, then use highest ns value
if [ $value -le 99 ]; then
	echo -n "optimal value for lapic_timer_advance_ns is: "
	awk "NR==$(($i - 1))" $1 | cut -f 1 -d ":"
	exit 0
fi
echo optimal not found
exit 1
