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

import os, copy
import tuned.plugins
import tuned.logs
import tuned.monitors
import tuned.utils.storage
import struct
from subprocess import *
from functools import wraps

log = tuned.logs.get()

# command decorator
def command(plugin, key):
	"""
	This decorator makes adding new commands easier. The only thing you have to do is
	to implement method which handles the value of particular option from config file
	and returns previosly set value.
	
	Here is example of method like that:
		@command("disk", "elevator")
		def _set_elevator(self, dev, value):
			sys_file = os.path.join("/sys/block/", dev, "queue/scheduler")
			old_value = tuned.utils.commands.read_file(sys_file)
			tuned.utils.commands.write_to_file(sys_file, value)
			return old_value

	This decorator works then like this:
		1. Tries to revert to previously stored value in Storage class
		2. Tries to set the new value
		3. Stores old value returned by the original method into Storage
	"""
	def my_decorator(target):
		def wrapper(self, *args, **kwargs):
			# Find out if the original method is def method(self, dev, value)
			# or just def method(self, value) and set the variables.
			dev = ""
			value = None
			if len(args) == 1:
				value = args[0]
			else:
				dev = "_" + args[0]
				value = args[1]

			# Check if this plugin has key in Storage cache
			storage = tuned.utils.storage.Storage.get_instance()
			if not storage.data.has_key(plugin):
				log.error("Storage file does not contain item with key %s" % (plugin))
				return

			# Revert to previous value if it exists
			if storage.data[plugin].has_key(key + dev):
				old_value = storage.data[plugin][key + dev]
				# Plugin could call Plugin.register_command with revert_fnc
				# set, so we should try to use specialized method for reverting.
				# However, if there's no method like that, use the original method
				# this decorator decorates.
				revert_fnc = self._commands[key][2]
				if not revert_fnc:
					if len(dev) == 0:
						target(self, old_value)
					else:
						target(self, dev[1:], old_value)
					del storage.data[plugin][key + dev]
				else:
					if len(dev) == 0:
						revert_fnc(old_value)
					else:
						revert_fnc(dev[1:], old_value)

			# set it to new state and store old_value
			if not value or len(value) == 0:
				return False

			old_value = target(self, *args, **kwargs)
			if len(old_value) != 0:
				storage.data[plugin][key + dev] = old_value
				storage.save()
			return True

		# Fix the wrapper's call signature
		return wraps(target)(wrapper)

	return my_decorator

# command_revert decorator
def command_revert(plugin, key):
	def my_decorator(target):
		def wrapper(self, *args, **kwargs):
			dev = ""
			value = None
			if len(args) == 1:
				value = args[0]
			else:
				dev = "_" + args[0]
				value = args[1]

			# revert to previous state
			storage = tuned.utils.storage.Storage.get_instance()
			if not storage.data.has_key(plugin):
				log.error("Storage file does not contain item with key %s" % (plugin))
				return

			if storage.data[plugin].has_key(key + dev):
				old_value = storage.data[plugin][key + dev]
				if len(dev) == 0:
					target(self, old_value)
				else:
					target(self, dev[1:], old_value)
				del storage.data[plugin][key + dev]
			return True

		# Fix the wrapper's call signature
		return wraps(target)(wrapper)

	return my_decorator

def write_to_file(f, data):
	log.debug("Writing to file: %s < %s" % (f, data))
	try:
		fd = open(f, "w")
		fd.write(str(data))
		fd.close()
	except (OSError,IOError) as e:
		log.error("Writing to file %s error: %s" % (f, e))

def read_file(f):
	old_value = ""
	try:
		f = open(f, "r")
		old_value = f.read()
		f.close()
	except (OSError,IOError) as e:
		log.error("Reading %s error: %s" % (f, e))
	return old_value
	

def revert_file(key, subkey, f):
	storage = tuned.utils.storage.Storage.get_instance()
	if not storage.data.has_key(key):
		log.error("Storage file does not contain item with key %s" % (key))
		return

	if not storage.data[key].has_key(subkey):
		return

	old_value = storage.data[key][subkey]
	write_to_file(f, old_value)

	del storage.data[key][subkey]

def set_file(key, subkey, f, data):
	storage = tuned.utils.storage.Storage.get_instance()
	if not storage.data.has_key(key):
		log.error("Storage file does not contain item with key %s" % (key))
		return

	old_value = read_file(f)
	storage.data[key][subkey] = old_value
	storage.save()

	write_to_file(f, data)

def execute(args):
	out = ""
	try:
		proc = Popen(args, stdout=PIPE, stderr=PIPE)
		out, err = proc.communicate()

		if proc.returncode:
			log.error("Executing %s error: %s" % (args[0], err[:-1]))
	except (OSError,IOError) as e:
		log.error("Executing %s error: %s" % (args[0], e))
	return out

