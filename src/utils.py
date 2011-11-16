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

import signal

__all__ = ['handle_signal']

def handle_signal(signals, callback, pass_args = False):
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
