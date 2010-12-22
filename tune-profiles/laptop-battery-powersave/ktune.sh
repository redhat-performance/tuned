#!/bin/sh

. /etc/tune-profiles/functions

start() {
	set_disk_alpm min_power
	#enable_usb_autosuspend
	enable_cpu_multicore_powersave
	set_cpu_governor ondemand
	enable_snd_ac97_powersave
	disable_cd_polling
	enable_wifi_powersave
	eee_set_reduced_fsb

	return 0
}

stop() {
	set_disk_alpm max_performance
	#disable_usb_autosuspend
	disable_cpu_multicore_power_savings
	restore_cpu_scheduler
	enable_snd_ac97_powersave
	enable_cd_polling
	disable_wifi_powersave
	eee_set_normal_fsb

	return 0
}

process $@
