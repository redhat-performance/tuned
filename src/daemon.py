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

import logs
import atexit
import os
import signal
import sys

log = logs.get("tuned")

CONFIG_FILE = "/etc/tuned/tuned.conf"
INIT_TIMEOUT = 3

class Daemon(object):
	def __init__(self, config_file = None, debug = False):
		log.info("initializing")

		if config_file is None:
			config_file = CONFIG_FILE


		self._config_file = config_file
		self._debug = debug

	def daemonize(self):
		log.debug("daemonizing")

		parent_pid = os.getpid()

		signal.signal(signal.SIGALRM, self._daemonize_handle_signal)
		signal.signal(signal.SIGUSR1, self._daemonize_handle_signal)
		signal.signal(signal.SIGUSR2, self._daemonize_handle_signal)

		if self._daemonize_fork():
			os.kill(parent_pid, signal.SIGUSR1)
			log.debug("daemonizing done")
		else:
			os.kill(parent_pid, signal.SIGUSR2)
			log.critical("daemonizing failed")
			sys.exit(1)

		signal.signal(signal.SIGALRM, signal.SIG_DFL)
		signal.signal(signal.SIGUSR1, signal.SIG_DFL)
		signal.signal(signal.SIGUSR2, signal.SIG_DFL)

	def _daemonize_fork(self):
		try:
			pid = os.fork()
			if pid > 0:
				self._daemonize_wait()
				assert False # unreachable
		except OSError as e:
			log.critical("fork: %s", str(e))
			return false

		os.chdir("/")
		os.setsid()
		os.umask(0)

		try:
			pid = os.fork()
			if pid > 0:
				sys.exit(0)
		except OSError as e:
			log.cricital("fork: %s", str(e))
			return false

		si = file('/dev/null', 'r')
		so = file('/dev/null', 'a+')
		se = file('/dev/null', 'a+', 0)
		os.dup2(si.fileno(), sys.stdin.fileno())
		os.dup2(so.fileno(), sys.stdout.fileno())
		os.dup2(se.fileno(), sys.stderr.fileno())

		return True

	def _daemonize_wait(self):
		signal.alarm(INIT_TIMEOUT)
		while True:
			signal.pause()

	def _daemonize_handle_signal(self, signum, frame):
		if signum == signal.SIGUSR1:
			log.debug("daemonizing, got signal (success), exit")
			sys.exit(0)
		if signum == signal.SIGUSR2 or signum == signal.SIGALRM:
			log.critical("daemonizing, signal %d (failure), exit" % signum)
			sys.exit(1)
		else:
			log.warn("daemonizing, unknown signal %s, ignoring" % signum)

	def run_controller(self):
		pass

	def run(self):
		log.info("running")

		import time

		self._terminate = False
		while not self._terminate:
			time.sleep(1)

	def terminate(self):
		log.info("terminating")
		self._terminate = True

	def reload(self):
		log.info("reloading")
		pass

	def cleanup(self):
		# TODO: do we need it?
		raise Exception()
