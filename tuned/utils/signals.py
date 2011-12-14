__all__ = ["handle_signal"]

import signal

def handle_signal(signals, callback, pass_args = False):
	"""
	Set up signal handler for a given signal or a list of signals.
	"""
	if type(signals) is not list:
		signals = [signals]
	for signum in signals:
		_handle_signal(signum, callback, pass_args)

def _handle_signal(signum, callback, pass_args):
	if pass_args or callback in [signal.SIG_DFL, signal.SIG_IGN]:
		signal.signal(signum, callback)
	else:
		def handler_wrapper(_signum, _frame):
			if signum == _signum:
				callback()
		signal.signal(signum, handler_wrapper)
