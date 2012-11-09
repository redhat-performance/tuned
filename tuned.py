#!/usr/bin/python -Es
#
# tuned: daemon for monitoring and adaptive tuning of system devices
#
# Copyright (C) 2008-2012 Red Hat, Inc.
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
import traceback
import tuned.logs
import tuned.daemon
import tuned.exceptions

DBUS_BUS = "com.redhat.tuned"
DBUS_OBJECT = "/Tuned"
DBUS_INTERFACE = "com.redhat.tuned.control"

def error(message):
	print >>sys.stderr, message

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Daemon for monitoring and adaptive tuning of system devices.")
	parser.add_argument("--daemon", "-d", action="store_true", help="run on background")
	parser.add_argument("--debug", "-D", action="store_true", help="show/log debugging messages")
	parser.add_argument("--no-dbus", action="store_true", help="do not attach to DBus")
	parser.add_argument("--profile", "-p", action="store", type=str, metavar="name", help="tuning profile to be activated")

	args = parser.parse_args(sys.argv[1:])

	if os.geteuid() != 0:
		error("Superuser permissions are required to run the daemon.")
		sys.exit(1)

	log = tuned.logs.get()
	if args.debug:
		log.setLevel("DEBUG")

	try:
		app = tuned.daemon.Application(args.profile)

		if not args.no_dbus:
			app.attach_to_dbus(DBUS_BUS, DBUS_OBJECT, DBUS_INTERFACE)

		if args.daemon:
				app.daemonize()
				log.switch_to_file()

		app.run()

	except tuned.exceptions.TunedException as exception:
		if (args.debug):
			traceback.print_exc()
		else:
			error(str(exception))
			sys.exit(1)
