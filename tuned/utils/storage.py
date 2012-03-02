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

import tuned.patterns
import tuned.logs
import tuned.utils
import pickle

log = tuned.logs.get()

DEFAULT_STORAGE_FILE = "./save.pickle"

class Storage(tuned.patterns.Singleton):
	def __init__(self):
		super(self.__class__, self).__init__()
		self._data = {}
		self.load()

	@property
	def data(self):
		return self._data

	@data.setter
	def data(self, data):
		self._data.update(data)

	def save(self):
		try:
			log.debug("Storing %s" % (str(self._data)))
			with open(DEFAULT_STORAGE_FILE, "w") as f:
				pickle.dump(self._data, f)
		except (OSError,IOError) as e:
			log.error("Error saving storage file %s: %s" % (DEFAULT_STORAGE_FILE, e))

	def load(self):
		try:
			with open(DEFAULT_STORAGE_FILE, "r") as f:
				self._data = pickle.load(f)
		except (OSError,IOError) as e:
			log.error("Error loading storage file %s: %s" % (DEFAULT_STORAGE_FILE, e))
			self._data = {}
		except EOFError:
			self._data = {}

