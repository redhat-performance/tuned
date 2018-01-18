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

from __future__ import print_function
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
	f = open('/dev/null', 'w+')
	os.dup2(f.fileno(), sys.stdin.fileno())
	os.dup2(f.fileno(), sys.stdout.fileno())
	os.dup2(f.fileno(), sys.stderr.fileno())

def write_pidfile():
	with os.fdopen(os.open(PIDFILE, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o644), "w") as f:
		f.write("%d" % os.getpid())

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
	try:
		fd = os.open(filename, os.O_WRONLY)
	except OSError:
		print("Cannot open (%s)." % filename, file=sys.stderr)
		return None
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
	except Exception as e:
		print("Cannot daemonize (%s)." % e, file=sys.stderr)
		return False

	global pmqos_fds
	pmqos_fds = []

	for (name, value) in list(options.items()):
		try:
			new_fd = set_pmqos(name, value)
			if new_fd is not None:
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
	except IOError as e:
		if not force: print("Cannot open PID file (%s)." % e, file=sys.stderr)
		return False

	try:
		os.kill(daemon_pid, signal.SIGTERM)
	except OSError as e:
		if not force: print("Cannot terminate the daemon (%s)." % e, file=sys.stderr)
		return False

	try:
		os.unlink(PIDFILE)
	except OSError as e:
		if not force: print("Cannot delete the PID file (%s)." % e, file=sys.stderr)
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
			print("Invalid option (%s)." % option, file=sys.stderr)


	if disable:
		sys.exit(0 if kill_daemon() else 1)

	if len(options) == 0:
		print("No options set. Not starting.", file=sys.stderr)
		sys.exit(1)

	kill_daemon(True)
	run_daemon(options)
	sys.exit(1)
