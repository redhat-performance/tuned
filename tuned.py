#!/usr/bin/python -Es
#
# tuned: daemon for monitoring and adaptive tuning of system devices
#
# Copyright (C) 2008-2013 Red Hat, Inc.
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

from __future__ import print_function
import argparse
import os
import sys
import traceback
import tuned.logs
import tuned.daemon
import tuned.exceptions
import tuned.consts as consts
import tuned.version as ver
from tuned.utils.global_config import GlobalConfig

def error(message):
	print(message, file=sys.stderr)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description = "Daemon for monitoring and adaptive tuning of system devices.")
	parser.add_argument("--daemon", "-d", action = "store_true", help = "run on background")
	parser.add_argument("--debug", "-D", action = "store_true", help = "show/log debugging messages")
	parser.add_argument("--log", "-l", nargs = "?", const = consts.LOG_FILE, help = "log to file, default file: " + consts.LOG_FILE)
	parser.add_argument("--pid", "-P", nargs = "?", const = consts.PID_FILE, help = "write PID file, default file: " + consts.PID_FILE)
	parser.add_argument("--no-dbus", action = "store_true", help = "do not attach to DBus")
	parser.add_argument("--profile", "-p", action = "store", type=str, metavar = "name", help = "tuning profile to be activated")
	parser.add_argument('--version', "-v", action = "version", version = "%%(prog)s %s.%s.%s" % (ver.TUNED_VERSION_MAJOR, ver.TUNED_VERSION_MINOR, ver.TUNED_VERSION_PATCH))
	args = parser.parse_args(sys.argv[1:])

	if os.geteuid() != 0:
		error("Superuser permissions are required to run the daemon.")
		sys.exit(1)

	config = GlobalConfig()
	log = tuned.logs.get()
	if args.debug:
		log.setLevel("DEBUG")

	try:
		if args.daemon:
			if args.log is None:
				args.log = consts.LOG_FILE
			log.switch_to_file(args.log)
		else:
			if args.log is not None:
				log.switch_to_file(args.log)

		app = tuned.daemon.Application(args.profile, config)

		# no daemon mode doesn't need DBus
		if not config.get_bool(consts.CFG_DAEMON, consts.CFG_DEF_DAEMON):
			args.no_dbus = True

		if not args.no_dbus:
			app.attach_to_dbus(consts.DBUS_BUS, consts.DBUS_OBJECT, consts.DBUS_INTERFACE)

		# always write PID file
		if args.pid is None:
			args.pid = consts.PID_FILE

		if args.daemon:
			app.daemonize(args.pid)
		else:
			app.write_pid_file(args.pid)
		app.run(args.daemon)

	except tuned.exceptions.TunedException as exception:
		if (args.debug):
			traceback.print_exc()
		else:
			error(str(exception))
			sys.exit(1)
