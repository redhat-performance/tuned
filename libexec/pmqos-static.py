#!/usr/bin/python
#
# pmqos-static.py: Simple daemon for setting static PM QoS values. It is a part
#                  of 'tuned' and it should not be called manually.
#
# Copyright (C) 2011 Red Hat, Inc.
# Authors: Jan Vcelak <jvcelak@redhat.com>
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
import signal
import struct
import sys
import time

# Used interface is described in Linux kernel documentation:
# Documentation/power/pm_qos_interface.txt

ALLOWED_INTERFACES = [ "cpu_dma_latency", "network_latency", "network_throughput" ]
PIDFILE = "/var/run/tuned/pmqos-static.pid"

def do_fork():
	pid = os.fork()
	if pid > 0:
		sys.exit(0)

def close_fds():
	s_in = file('/dev/null', 'r')
	s_out = file('/dev/null', 'a+')
	s_err = file('/dev/null', 'a+', 0)
	os.dup2(s_in.fileno(), sys.stdin.fileno())
	os.dup2(s_out.fileno(), sys.stdout.fileno())
	os.dup2(s_err.fileno(), sys.stderr.fileno())

def write_pidfile():
	with open(PIDFILE, "w") as pidfile:
		pidfile.write("%s" % os.getpid())

def daemonize():
	do_fork()
	os.chdir("/")
	os.setsid()
	os.umask(0)
	do_fork()
	close_fds()

def set_pmqos(name, value):
	filename = "/dev/%s" % name
	bin_value = struct.pack("i", int(value))
	fd = os.open(filename, os.O_WRONLY)
	os.write(fd, bin_value)
	return fd

def sleep_forever():
	while True:
		time.sleep(86400)

def sigterm_handler(signum, frame):
	global pmqos_fds
	if type(pmqos_fds) is list:
		for fd in pmqos_fds:
			os.close(fd)
	sys.exit(0)

def run_daemon(options):
	try:
		daemonize()
		write_pidfile()
		signal.signal(signal.SIGTERM, sigterm_handler)
	except Exception, e:
		print >>sys.stderr, "Cannot daemonize (%s)." % e
		return False

	global pmqos_fds
	pmqos_fds = []

	for (name, value) in options.items():
		try:
			new_fd = set_pmqos(name, value)
			pmqos_fds.append(new_fd)
		except:
			# we are daemonized
			pass

	if len(pmqos_fds) > 0:
		sleep_forever()
	else:
		return False

def kill_daemon(force = False):
	try:
		with open(PIDFILE, "r") as pidfile:
			daemon_pid = int(pidfile.read())
	except IOError, e:
		if not force: print >>sys.stderr, "Cannot open PID file (%s)." % e
		return False

	try:
		os.kill(daemon_pid, signal.SIGTERM)
	except OSError, e:
		if not force: print >>sys.stderr, "Cannot terminate the daemon (%s)." % e
		return False

	try:
		os.unlink(PIDFILE)
	except OSError, e:
		if not force: print >>sys.stderr, "Cannot delete the PID file (%s)." % e
		return False

	return True

if __name__ == "__main__":

	disable = False
	options = {}

	for option in sys.argv[1:]:
		if option == "disable":
			disable = True
			break

		try:
			(name, value) = option.split("=")
		except ValueError:
			name = option
			value = None

		if name in ALLOWED_INTERFACES and len(value) > 0:
			options[name] = value
		else:
			print >>sys.stderr, "Invalid option (%s)." % option


	if disable:
		sys.exit(0 if kill_daemon() else 1)

	if len(options) == 0:
		print >>sys.stderr, "No options set. Not starting."
		sys.exit(1)

	kill_daemon(True)
	run_daemon(options)
	sys.exit(1)
