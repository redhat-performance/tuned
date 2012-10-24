__all__ = ["daemonize", "write_pidfile"]

import tuned.logs
import os
import signal
import sys

PIDFILE = "/run/tuned/tuned.pid"

log = tuned.logs.get()

def handle_signal(signals, handler, pass_args = True):
	for s in signals:
		signal.signal(s, handler)

def daemonize(timeout, pidfile = PIDFILE):
	"""
	Perform current process daemonization. Kills current SIGALRM, SIGUSR1, and SIGUSR2 signal handlers.
	"""
	parent_pid = os.getpid()
	handle_signal([signal.SIGALRM, signal.SIGUSR1, signal.SIGUSR2], _daemonize_handle_signal, pass_args=True)

	if _daemonize_fork(timeout, pidfile):
		os.kill(parent_pid, signal.SIGUSR1)
		result = True
	else:
		os.kill(parent_pid, signal.SIGUSR2)
		result = False

	handle_signal([signal.SIGALRM, signal.SIGUSR1, signal.SIGUSR2], signal.SIG_DFL)
	return result

def write_pidfile(pidfile = PIDFILE):
	try:
		if not os.path.exists(os.path.dirname(pidfile)):
			os.makedirs(os.path.dirname(pidfile))
		with open(pidfile, "w") as f:
			f.write(str(os.getpid()))
	except (OSError,IOError) as e:
		log.critical("Cannot write the PID to %s: %s" % (pidfile, str(e)))

def _daemonize_fork(timeout, pidfile):
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

	write_pidfile(pidfile)

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
