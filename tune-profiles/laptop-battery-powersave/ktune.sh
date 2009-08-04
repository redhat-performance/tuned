#!/bin/sh

ALPM="min_power"

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

# Enables USB autosuspend for all devices
for i in /sys/bus/usb/devices/*/power/autosuspend; do echo 1 > $i; done

# Enables multi core power savings for low wakeup systems
[ -e /sys/devices/system/cpu/sched_mc_power_savings ] && echo 1 > /sys/devices/system/cpu/sched_mc_power_savings

# Enable ondemand governor (best for powersaving)
[ -e /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ] && echo ondemand > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

# Enable AC97 audio power saving
[ -e /sys/module/snd_ac97_codec/parameters/power_save ] && echo Y > /sys/module/snd_ac97_codec/parameters/power_save

# Disable HAL polling of CDROMS
for i in /dev/scd*; do hal-disable-polling --device $i; done

# Enable power saving mode for Wi-Fi cards
for i in /sys/bus/pci/devices/*/power_level ; do echo 5 > $i ; done
