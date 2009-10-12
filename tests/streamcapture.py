#
# Copyright (C) 2008, 2009 Red Hat, Inc.
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

import sys, StringIO

class StreamCapture:

	__capture = None
	__stdout = None

	def __init__(self):
		self.__stdout = sys.stdout
		self.__capture = StringIO.StringIO()

	def capture(self):
		sys.stdout = self.__capture

	def stdout(self):
		sys.stdout = self.__stdout

	def getcaptured(self):
		return self.__capture.getvalue()

	def clean(self):
		self.__capture.close()
		self.__capture = StringIO.StringIO()

	def close(self):
		self.__capture.close()		

	def __del__(self):
		try: sys.stdout = self.__stdout
		except: pass
		try: self.__capture.close()
		except: pass

capture = StreamCapture()
