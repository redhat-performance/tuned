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
import sys
import traceback
import tuned.admin
import tuned.consts as consts
import tuned.version as ver
from tuned.utils.global_config import GlobalConfig

def check_positive(value):
	try:
		val = int(value)
	except ValueError:
		val = -1
	if val <= 0:
		raise argparse.ArgumentTypeError("%s has to be >= 0" % value)
	return val

def check_log_level(value):
	try:
		return consts.CAPTURE_LOG_LEVELS[value.lower()]
	except KeyError:
		levels = ", ".join(consts.CAPTURE_LOG_LEVELS.keys())
		raise argparse.ArgumentTypeError(
				"Invalid log level: %s. Valid log levels: %s."
				% (value, levels))

if __name__ == "__main__":
	config = GlobalConfig()
	parser = argparse.ArgumentParser(description="Manage tuned daemon.")
	parser.add_argument('--version', "-v", action = "version", version = "%%(prog)s %s.%s.%s" % (ver.TUNED_VERSION_MAJOR, ver.TUNED_VERSION_MINOR, ver.TUNED_VERSION_PATCH))
	parser.add_argument("--debug", "-d", action="store_true", help="show debug messages")
	parser.add_argument("--async", "-a", action="store_true", help="with dbus do not wait on commands completion and return immediately")
	parser.add_argument("--timeout", "-t", default = consts.ADMIN_TIMEOUT, type = check_positive, help="with sync operation use specific timeout instead of the default %d second(s)" % consts.ADMIN_TIMEOUT)
	levels = ", ".join(consts.CAPTURE_LOG_LEVELS.keys())
	help = "level of log messages to capture (one of %s). Default: %s" \
			% (levels, consts.CAPTURE_LOG_LEVEL)
	parser.add_argument("--loglevel", "-l",
			default = consts.CAPTURE_LOG_LEVEL,
			type = check_log_level,
			help = help)

	subparsers = parser.add_subparsers()

	parser_list = subparsers.add_parser("list", help="list available profiles")
	parser_list.set_defaults(action="list")

	parser_active = subparsers.add_parser("active", help="show active profile")
	parser_active.set_defaults(action="active")

	parser_off = subparsers.add_parser("off", help="switch off all tunings")
	parser_off.set_defaults(action="off")

	parser_profile = subparsers.add_parser("profile", help="switch to a given profile, or list available profiles if no profile is given")
	parser_profile.set_defaults(action="profile")
	parser_profile.add_argument("profiles", metavar="profile", type=str, nargs="*", help="profile name")

	parser_profile_info = subparsers.add_parser("profile_info", help="show information/description of given profile or current profile if no profile is specified")
	parser_profile_info.set_defaults(action="profile_info")
	parser_profile_info.add_argument("profile", metavar="profile", type=str, nargs="?", default="", help="profile name, current profile if not specified")

	if config.get(consts.CFG_RECOMMEND_COMMAND, consts.CFG_DEF_RECOMMEND_COMMAND):
		parser_off = subparsers.add_parser("recommend", help="recommend profile")
		parser_off.set_defaults(action="recommend_profile")

	parser_verify = subparsers.add_parser("verify", help="verify profile")
	parser_verify.set_defaults(action="verify_profile")
	parser_verify.add_argument("--ignore-missing", "-i", action="store_true", help="do not treat missing/non-supported tunings as errors")

	parser_auto_profile = subparsers.add_parser("auto_profile", help="enable automatic profile selection mode, switch to the recommended profile")
	parser_auto_profile.set_defaults(action="auto_profile")

	parser_profile_mode = subparsers.add_parser("profile_mode", help="show current profile selection mode")
	parser_profile_mode.set_defaults(action="profile_mode")

	args = parser.parse_args(sys.argv[1:])

	options = vars(args)
	debug = options.pop("debug")
	async = options.pop("async")
	timeout = options.pop("timeout")
	action_name = options.pop("action")
	log_level = options.pop("loglevel")
	result = False

	dbus = config.get_bool(consts.CFG_DAEMON, consts.CFG_DEF_DAEMON)

	try:
		admin = tuned.admin.Admin(dbus, debug, async, timeout, log_level)

		result = admin.action(action_name, **options)
	except:
		traceback.print_exc()
		sys.exit(3)

	if result == False:
		sys.exit(1)
	else:
		sys.exit(0)
