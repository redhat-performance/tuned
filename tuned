#!/usr/bin/python
#
# tuned: A simple daemon that performs monitoring and adaptive configuration
#        of devices in the system
#
# Copyright (C) 2008, 2009 Red Hat, Inc.
# Authors: Phil Knirsch
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

import sys, os.path, getopt, atexit, signal

TUNEDDIR = "/usr/share/tuned"
if not TUNEDDIR in sys.path:
	sys.path.append(TUNEDDIR)

import logging, tuned_logging
log = logging.getLogger("tuned")

def usage():
	print "Usage: tuned [-d|--daemon] [-c conffile|--config=conffile] [-D|--debug]"

def handler(signum, frame):
	log.debug("Received signal number %d." % signum)
	sys.exit()

def daemonize():
	log.debug("Daemonizing")

	try:
		pid = os.fork()
		if pid > 0:
			sys.exit(0)
	except OSError, e:
		log.critical("Cannot fork: %s", str(e))
		sys.exit(1)

	os.chdir("/")
	os.setsid()
	os.umask(0)

	try:
		pid = os.fork()
		if pid > 0:
			sys.exit(0)
	except OSError, e:
		log.cricital("Cannot fork: %s", str(e))
		sys.exit(1)

	si = file('/dev/null', 'r')
	so = file('/dev/null', 'a+')
	se = file('/dev/null', 'a+', 0)
	os.dup2(si.fileno(), sys.stdin.fileno())
	os.dup2(so.fileno(), sys.stdout.fileno())
	os.dup2(se.fileno(), sys.stderr.fileno())

if __name__ == "__main__":
	try:
		opts, args = getopt.getopt(sys.argv[1:], "dc:D", ["daemon", "config=", "debug"])
	except getopt.error, e:
		print >>sys.stderr, ("Error parsing command-line arguments: %s" % e)
		usage()
	        sys.exit(1)

	if len(args) > 0:
		print >>sys.stderr, ("Too many arguments.")
		usage()
		sys.exit(1)

	daemon = False
	cfgfile = "/etc/tuned.conf"
	debug = False
	is_superuser = os.getuid() == 0

	for (opt, val) in opts:
		if   opt in ['-d', "--daemon"]:
			daemon = True
		elif opt in ['-c', "--config"]:
			cfgfile = val
		elif opt in ['-D', "--debug"]:
			debug = True

	if not is_superuser:
		if daemon:
			log.critical("Superuser permissions are needed.")
			sys.exit(1)
		else:
			log.warn("Superuser permissions are needed. Most tunings will not work!")

	if daemon:
		log.switchToFile()
		daemonize()

	from tuned import tuned
	tuned.init(TUNEDDIR, cfgfile, debug = debug)

	atexit.register(logging.shutdown)
	atexit.register(tuned.cleanup)
	signal.signal(signal.SIGTERM, handler)

	tuned.run()
	tuned.cleanup()
