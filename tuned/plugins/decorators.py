# Copyright (C) 2008-2012 Red Hat, Inc.
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

__all__ = ["command_set", "command_get"]

#	@command_set("scheduler", per_device=True)
#	def set_scheduler(self, value, device):
#		set_new_scheduler
#
#	@command_get("scheduler")
#	def get_scheduler(self, device):
#		return current_scheduler
#
#	@command_set("foo")
#	def set_foo(self, value):
#		set_new_foo
#
#	@command_get("foo")
#	def get_foo(self):
#		return current_foo
#

def command_set(name, per_device=False):
	def wrapper(method):
		method._command = {
			"set": True,
			"name": name,
			"per_device": per_device,
		}
		return method

	return wrapper

def command_get(name):
	def wrapper(method):
		method._command = { "get": True }
		return method
	return wrapper
