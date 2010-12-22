#!/bin/sh

. /etc/tune-profiles/functions

start() {
	set_disk_alpm min_power
	return 0
}

stop() {
	set_disk_alpm max_performance
	return 0
}

process $@
