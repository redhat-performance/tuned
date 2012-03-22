#!/bin/sh

. /etc/tune-profiles/functions

start() {
	echo 1 > /tmp/test.txt
	return 0
}

stop() {
	return 0
}

process $@
