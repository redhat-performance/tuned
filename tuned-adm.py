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

import argparse
import sys
import traceback
import tuned.admin
import tuned.consts as consts
import tuned.version as ver

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Manage tuned daemon.")
	parser.add_argument('--version', "-v", action = "version", version = "%%(prog)s %s.%s.%s" % (ver.TUNED_VERSION_MAJOR, ver.TUNED_VERSION_MINOR, ver.TUNED_VERSION_PATCH))
	parser.add_argument("--debug", action="store_true", help=argparse.SUPPRESS)
	subparsers = parser.add_subparsers()

	parser_list = subparsers.add_parser("list", help="list available profiles")
	parser_list.set_defaults(action="list")

	parser_active = subparsers.add_parser("active", help="show active profile")
	parser_active.set_defaults(action="active")

	parser_off = subparsers.add_parser("off", help="switch off all tunings")
	parser_off.set_defaults(action="off")

	parser_profile = subparsers.add_parser("profile", help="switch to a given profile")
	parser_profile.set_defaults(action="profile")
	parser_profile.add_argument("profiles", metavar="profile", type=str, nargs="+", help="profile name")

	parser_off = subparsers.add_parser("recommend", help="recommend profile")
	parser_off.set_defaults(action="recommend_profile")

	args = parser.parse_args(sys.argv[1:])

	options = vars(args)
	debug = options.pop("debug")
	action_name = options.pop("action")
	result = False

	try:
		controller = tuned.admin.DBusController(consts.DBUS_BUS, consts.DBUS_OBJECT, consts.DBUS_INTERFACE)
		admin = tuned.admin.Admin(controller)

		action = getattr(admin, action_name)
		result = action(**options)
	except tuned.admin.TunedAdminException as e:
		if not debug:
			print >>sys.stderr, e
		else:
			traceback.print_exc()
		sys.exit(2)
	except:
		traceback.print_exc()
		sys.exit(3)

	if result == False:
		sys.exit(1)
	else:
		sys.exit(0)
