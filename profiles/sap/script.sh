#!/bin/bash

# SAP ktune script
#
# TODO: drop this script and implement native support
#       into plugins

. /usr/lib/tuned/functions

start() {
	# The following lines are for autodetection of SAP settings
	SAP_MAIN_MEMORY_TOTAL=`awk '/MemTotal:/ {print $2}' /proc/meminfo`
	SAP_SWAP_SPACE_TOTAL=`awk '/SwapTotal:/ {print $2}' /proc/meminfo`
	# Rounding to full Gigabytes
	SAP_VIRT_MEMORY_TOTAL=$(( ( $SAP_MAIN_MEMORY_TOTAL + $SAP_SWAP_SPACE_TOTAL + 1048576 ) / 1048576 ))

	# kernel.shmall is in 4 KB pages; minimum 20 GB (SAP Note 941735)
	SAP_SHMALL=$(( $SAP_VIRT_MEMORY_TOTAL * 1024 * 1024 / 4 ))
	# kernel.shmmax is in Bytes; minimum 20 GB (SAP Note 941735)
	SAP_SHMMAX=$(( $SAP_VIRT_MEMORY_TOTAL * 1024 * 1024 * 1024 ))
	CURR_SHMALL=`sysctl -n kernel.shmall`
	CURR_SHMMAX=`sysctl -n kernel.shmmax`
	save_value kernel.shmall "$CURR_SHMALL"
	save_value kernel.shmmax "$CURR_SHMMAX"
	(( $SAP_SHMALL > $CURR_SHMALL )) && sysctl -w kernel.shmall="$SAP_SHMALL"
	(( $SAP_SHMMAX > $CURR_SHMMAX )) && sysctl -w kernel.shmmax="$SAP_SHMMAX"

	return 0
}

stop() {
	SHMALL=`restore_value kernel.shmall`
	SHMMAX=`restore_value kernel.shmmax`
	[ "$SHMALL" ] && sysctl -w kernel.shmall="$SHMALL"
	[ "$SHMMAX" ] && sysctl -w kernel.shmmax="$SHMMAX"

	return 0
}

process $@
