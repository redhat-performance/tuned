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

import argparse
import os
import sys
import tuned.application
import tuned.logs

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Daemon for monitoring and adaptive tuning of system devices.")
	parser.add_argument("--daemon", "-d", action="store_true", help="run on background")
	parser.add_argument("--debug", "-D", action="store_true", help="show/log debugging messages")
	parser.add_argument("--no-dbus", action="store_true", help="do not attach to DBus")
	parser.add_argument("--profile", "-p", action="store", type=str, metavar="name", help="tuning profile to be activated")

	args = parser.parse_args(sys.argv[1:])

	log = tuned.logs.get()
	if (args.debug):
		log.setLevel("DEBUG")

	if os.geteuid() != 0:
		if args.daemon:
			log.critical("Superuser permissions are needed.")
			sys.exit(1)
		else:
			log.warn("Superuser permissions are needed. Most tunings will not work!")

	app = tuned.application.Application(args.profile, not args.no_dbus)

	if args.daemon:
		log.switch_to_file()
		if tuned.utils.daemonize(3):
			log.debug("successfully daemonized")
		else:
			log.critical("cannot daemonize")
			sys.exit(1)
	else:
		tuned.utils.write_pidfile()

	app.run()
