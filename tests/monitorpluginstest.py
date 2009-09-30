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

import sys, os, ConfigParser

class MonitorPluginsTest:
	def __init__(self, tunedir):

		self.tunedir = tunedir

		# fake configuration
		self.config = ConfigParser.RawConfigParser()
		#self.config.add_section("main")
		#self.config.set("main", "interval", 10)

	def run(self):
		plugins = map(
			lambda f: f[:-3], # remove .py
			filter( # only modules
				lambda f: f[0] != "." and f[-3:] == ".py" and f != "__init__.py",
				os.listdir(self.tunedir + "/monitorplugins")
			))

		if len(plugins) == 0:
			print "No monitor plugins found."
			return False

		print "Found monitor plugins:"
		for p in plugins:
			print "* %s" % (p)
			self._checkPlugin(p)

	def _checkPlugin(self, plugin):

		# module loading
		print " - import"
		try:
			exec "from monitorplugins.%s import _plugin" % (plugin)
		except Exception as e:
			print "    failed: %s %s" % (e, type(e))
			return False


		# module initialization
		print " - init()"
		try:
			_plugin.init(self.config)
		except Exception as e:
			print "    failed: %s %s" % (e, type(e))
			return False

		# module get test data
		print " - getLoad()"
		try:
			if _plugin.getLoad() == None:
				raise Exception("plugin returned None as a result")
		except Exception as e:
			print "    failed: %s %s" % (e, type(e))

		# module cleanup
		print " - cleanup()"
		try:
			_plugin.cleanup()
		except Exception as e:
			print "    failed: %s %s" % (e, type(e))

