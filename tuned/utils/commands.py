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

log = tuned.logs.get()


def write_to_file(f, data):
	log.debug("Writing to file: %s < %s" % (f, data))
	try:
		fd = open(f, "w")
		fd.write(data)
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

