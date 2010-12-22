#!/bin/sh

. /etc/tune-profiles/functions

start() {
	set_cpu_governor performance

	return 0
}

stop() {
	restore_cpu_governor

	return 0
}

process $@
