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

class Logging:

	__indent = 0
	__testFinished = True
	__info = []

	def __init__(self):
		pass

	def end(self):
		if not self.__testFinished:
			print
			self.__infoFlush()
			self.__indent = 0
		print

	def section(self, info):
		print
		print "== %s ==" % info
		print
		self.__indent = 0

	def indent(self):
		self.__indent += 1

	def unindent(self):
		self.__indent -= 1

	def test(self, info):
		if not self.__testFinished:
			print
			self.__infoFlush()

		self.__testFinished = False
		i = self.__indent
		self.__info = []

		if i == 0: bullet = "* "
		elif i == 1: bullet = "+ "
		elif i == 2: bullet = "- "
		else: bullet = "? "

		print (i * "  ") + bullet + info, 

	def info(self, info):
		self.__info.append(str(info))
		if self.__testFinished:
			self.__infoFlush()

	def __infoFlush(self):
		for i in self.__info:
			print ((self.__indent + 1) * "  ") + "> " + i
		self.__info = []

	def result(self, failinfo = None):
		if failinfo == None:
			print ": success"
		else:
			print ": failed"
			self.info(failinfo)

		self.__infoFlush()
		self.__testFinished = True

	def result_e(self, exception):
		print ": failed"

		if not exception == None:
			self.info("Exception: %s, %s" % (exception, type(exception)))
		self.__infoFlush()
		self.__testFinished = True

log = Logging()

