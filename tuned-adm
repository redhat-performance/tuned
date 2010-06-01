#!/usr/bin/python
#
# tuned-adm: A command line utility for switching between user 
#            definable tuning profiles.
#
# Copyright (C) 2008, 2009 Red Hat, Inc.
# Authors: Marcela Maslanova
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

import os
import sys
import locale

def usage():
	print """
Usage: tuned-adm <command>

commands:
  help                           show this help message and exit
  list                           list all available and active profiles
  active                         show current active profile
  off                            switch off all tunning
  profile <profile-name>         switch to given profile
"""

if __name__ == "__main__":
	args = sys.argv[1:]

	if len(args) < 1:
		print >>sys.stderr, "Missing arguments."
		usage()
		sys.exit(1)

	if args[0] in [ "help", "--help", "-h" ]:
		usage()
		sys.exit(0)

	TUNEDDIR="/usr/share/tuned"
	if TUNEDDIR not in sys.path:
		sys.path.insert(0, TUNEDDIR)

	from tuned_adm import tuned_adm
	tuned_adm.run(args)

