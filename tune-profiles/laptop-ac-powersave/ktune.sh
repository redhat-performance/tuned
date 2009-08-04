#!/bin/sh

ALPM="medium_power"

# Set ALPM for all host adapters that support it
for x in /sys/bus/scsi/devices/host*/scsi_host/host*/; do
	hotplug="0"
	if [ -e $x/sata_hotplug ]; then
		hotplug="$(cat $x/sata_hotplug)"
	fi
	if [ "$hotplug" == "0" -a -e $x/link_power_management_policy ]; then
		echo $ALPM > $x/link_power_management_policy
	fi
done
