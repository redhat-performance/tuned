#!/usr/bin/python
#
# tuned: A simple daemon that performs monitoring and adaptive configuration
#        of devices in the system
#
# Copyright (C) 2008-2011 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#

import tuned
import atexit
import getopt
import os
import signal
import sys

def usage():
	print "Usage: tuned [-d|--daemon] [-c conffile|--config=conffile] [-D|--debug]"

def error(message):
	print >>sys.stderr, message

if __name__ == "__main__":
	try:
		opts, args = getopt.getopt(sys.argv[1:], "dc:D", ["daemon", "config=", "debug"])
	except getopt.error as e:
		error("Error parsing command-line arguments: %s" % e)
		usage()
	        sys.exit(1)

	if len(args) > 0:
		error("Too many arguments.")
		usage()
		sys.exit(1)

	config_file = None
	daemon = False
	debug = False

	for (opt, val) in opts:
		if   opt in ['-d', "--daemon"]:
			daemon = True
		elif opt in ['-c', "--config"]:
			config_file = val
		elif opt in ['-D', "--debug"]:
			debug = True

	log = tuned.logs.get()
	if (debug):
		log.setLevel("DEBUG")

	if os.getuid() != 0:
		if daemon:
			log.critical("Superuser permissions are needed.")
			sys.exit(1)
		else:
			log.warn("Superuser permissions are needed. Most tunings will not work!")

	tuned_daemon = tuned.Daemon(config_file, debug)

	tuned.utils.handle_signal(signal.SIGHUP, tuned_daemon.reload)
	tuned.utils.handle_signal([signal.SIGINT, signal.SIGTERM], tuned_daemon.terminate)

	if daemon:
		log.switch_to_file()
		tuned_daemon.daemonize()

	atexit.register(tuned_daemon.cleanup)

	tuned_daemon.run()
