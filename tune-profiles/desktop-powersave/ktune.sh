#!/bin/sh

. /etc/tune-profiles/functions

start() {
	set_disk_alpm min_power
	set_radeon_powersave auto
	return 0
}

stop() {
	set_disk_alpm max_performance
	set_radeon_powersave default
	return 0
}

process $@
