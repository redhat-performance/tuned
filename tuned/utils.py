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

__all__ = ["handle_signal", "daemonize"]

import logs
import os
import signal
import sys

log = logs.get("tuned")

def handle_signal(signals, callback, pass_args = False):
	"""
	Set up signal handler for a given signal or a list of signals.
	"""
	if type(signals) is not list:
		signals = [signals]
	for signum in signals:
		_handle_signal(signum, callback, pass_args)

def _handle_signal(signum, callback, pass_args):
	if pass_args or signum in [signal.SIG_DFL, signal.SIG_IGN]:
		signal.signal(signum, callback)
	else:
		def handler_wrapper(_signum, _frame):
			if signum == _signum:
				callback()
		signal.signal(signum, handler_wrapper)

def daemonize(timeout):
	"""
	Perform current process daemonization. Kills current SIGALRM, SIGUSR1, and SIGUSR2 signal handlers.
	"""
	parent_pid = os.getpid()
	handle_signal([signal.SIGALRM, signal.SIGUSR1, signal.SIGUSR2], _daemonize_handle_signal, pass_args=True)

	if _daemonize_fork(timeout):
		os.kill(parent_pid, signal.SIGUSR1)
		result = True
	else:
		os.kill(parent_pid, signal.SIGUSR2)
		result = False

	handle_signal([signal.SIGALRM, signal.SIGUSR1, signal.SIGUSR2], signal.SIG_DFL)
	return result

def _daemonize_fork(timeout):
	try:
		pid = os.fork()
		if pid > 0:
			_daemonize_wait(timeout)
			assert False
	except OSError as e:
		log.critical("fork: %s", str(e))
		return False

	os.chdir("/")
	os.setsid()
	os.umask(0)

	try:
		pid = os.fork()
		if pid > 0:
			sys.exit(0)
	except OSError as e:
		log.cricital("fork: %s", str(e))
		return False

	si = file('/dev/null', 'r')
	so = file('/dev/null', 'a+')
	se = file('/dev/null', 'a+', 0)
	os.dup2(si.fileno(), sys.stdin.fileno())
	os.dup2(so.fileno(), sys.stdout.fileno())
	os.dup2(se.fileno(), sys.stderr.fileno())

	return True

def _daemonize_wait(timeout):
	signal.alarm(timeout)
	while True:
		signal.pause()

def _daemonize_handle_signal(signum, frame):
	if signum == signal.SIGUSR1:
		log.debug("daemonizing, got signal (success), exit")
		sys.exit(0)
	if signum == signal.SIGUSR2 or signum == signal.SIGALRM:
		log.critical("daemonizing, signal %d (failure), exit" % signum)
		sys.exit(1)
	else:
		log.warn("daemonizing, unknown signal %s, ignoring" % signum)
