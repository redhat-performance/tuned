#!/usr/bin/python -Es
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

import tuned.application
import tuned.logs
import getopt
import os
import sys

def usage():
	print "Usage: tuned [-d|--daemon] [-p name|--profile=name] [--no-dbus] [-D|--debug]"

def error(message):
	print >>sys.stderr, message

if __name__ == "__main__":
	try:
		opts, args = getopt.getopt(sys.argv[1:], "dp:D", ["daemon", "profile=", "debug", "no-dbus"])
	except getopt.error as e:
		error("Error parsing command-line arguments: %s" % e)
		usage()
		sys.exit(1)

	if len(args) > 0:
		error("Too many arguments.")
		usage()
		sys.exit(1)

	profile = None
	daemonize = False
	debug = False
	dbus = True

	for (opt, val) in opts:
		if   opt in ["-d", "--daemon"]:
			daemonize = True
		elif opt in ["-p", "--profile"]:
			profile = val
		elif opt in ["-D", "--debug"]:
			debug = True
		elif opt == "--no-dbus":
			dbus = False

	log = tuned.logs.get()
	if (debug):
		log.setLevel("DEBUG")

	if os.geteuid() != 0:
		if daemonize:
			log.critical("Superuser permissions are needed.")
			sys.exit(1)
		else:
			log.warn("Superuser permissions are needed. Most tunings will not work!")

	app = tuned.application.Application(profile, dbus)

	if daemonize:
		log.switch_to_file()
		if tuned.utils.daemonize(3):
			log.debug("successfully daemonized")
		else:
			log.critical("cannot daemonize")
			sys.exit(1)
	else:
		tuned.utils.write_pidfile()

	app.run()
