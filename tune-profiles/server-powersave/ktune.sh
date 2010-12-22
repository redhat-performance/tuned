#!/bin/sh

. /etc/tune-profiles/functions

start() {
	set_disk_alpm min_power
	disable_cd_polling

	return 0
}

stop() {
	set_disk_alpm max_performance
	enable_cd_polling

	return 0
}

process $@
