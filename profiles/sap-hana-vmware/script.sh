#!/bin/bash

# SAP ktune script
#
# TODO: drop this script and implement native support
#       into plugins

. /usr/lib/tuned/functions

start() {
	ethtool -K eth0 lro off

	return 0
}

stop() {
	ethtool -K eth0 lro on

	return 0
}

process $@
