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

import os, ConfigParser

class PluginsTester:

	def __init__(self, tunedir):

		self.tunedir = tunedir
		self.mp_dir = "monitorplugins"
		self.tp_dir = "tuningplugins"

		self.config = ConfigParser.RawConfigParser()

	def run(self):

		self.__checkPlugins()

	def __getPluginsFromDir(self, dir):

		files = os.listdir(self.tunedir + "/" + dir);
		plugins = filter(lambda f: f[0] != "." and f[-3:] == ".py" and f != "__init__.py", files) 
		plugins = map(lambda f: f[:-3], plugins)
		plugins.sort()

		return plugins

	### reporting tests progress

	def __reportTestBegin(self, info):
		print " * %s" % (info)

	def __reportTestStep(self, info):
		self.__testStep = info

	def __reportTestResult(self, exception = None):
		if exception == None:
			print "    - %s: success" % (self.__testStep)
		else:
			print "    - %s: failed (%s, %s)" % (self.__testStep, exception, type (exception))
	def __reportTestSkip(self, info):
		print "    - %s: skipped, %s" % (self.__testStep, info)

	### testing

	def __checkPlugins(self):

		monitorplugins = self.__getPluginsFromDir(self.mp_dir)
		tuningplugins = self.__getPluginsFromDir(self.tp_dir)

		# check plugins availability

		print "checking plugins availablity"

		self.__checkSiblingPlugins(monitorplugins, tuningplugins)

		print

		# monitor plugins test

		print "monitor plugins test"
		if len(monitorplugins) == 0:
			print " - no plugins found"

		monitor_results = {}

		for mp in monitorplugins:
			load = self.__testMonitorPlugin(mp)
			monitor_results[mp] = load

		print

		# tuning plugins test

		print "tunning plugins test"
		if len(tuningplugins) == 0:
			print " - no plugins found"

		for tp in tuningplugins:
			try:
				load = monitor_results[tp]
			except:
				load = None
			self.__testTuningPlugin(tp, load)

	def __checkSiblingPlugins(self, monitorplugins, tuningplugins):

		ok = True

		for mp in monitorplugins:
			if tuningplugins.count(mp) != 1:
				ok = False
				print " - monitor plugin '%s' misses tuning plugin" % mp

		for tp in tuningplugins:
			if monitorplugins.count(tp) != 1:
				ok = False
				print " - tuning plugin '%s' misses monitor plugin" % tp

		if ok:
			print " - monitor and tuning plugins match"

	def __testMonitorPlugin(self, name):

		self.__reportTestBegin("monitor plugin: %s" % (name))

		# initialization

		self.__reportTestStep("initialization")
		try:
			exec "from %s.%s import _plugin" % (self.mp_dir, name)
		except Exception as e:
			self.__reportTestResult(e)
			return None
		self.__reportTestResult()

		# init()

		self.__reportTestStep("call init()")
		try:
			_plugin.init(self.config)
		except Exception as e:
			self.__reportTestResult(e)
			return None
		self.__reportTestResult()

		# getLoad()

		self.__reportTestStep("call getLoad()")
		try:
			load = _plugin.getLoad()
			if load == None:
				raise Exception("Plugin returned None as a result.")
		except Exception as e:
			self.__reportTestResult(e)
			return None
		self.__reportTestResult()

		# cleanup()

		self.__reportTestStep("call cleanup()")
		try:
			_plugin.cleanup()
		except Exception as e:
			self.__reportTestResult(e)
			return None
		self.__reportTestResult()

		return load

	def __testTuningPlugin(self, name, load):

		self.__reportTestBegin("tuning plugin: %s" % (name))

		# initialization

		self.__reportTestStep("initialization")
		try:
			exec "from %s.%s import _plugin" % (self.tp_dir, name)
		except Exception as e:
			self.__reportTestResult(e)
			return False
		self.__reportTestResult()

		# init()

		self.__reportTestStep("call init()")
		try:
			_plugin.init(self.config)
		except Exception as e:
			self.__reportTestResult(e)
			return False
		self.__reportTestResult()

		# setTuning()

		self.__reportTestStep("call setTuning()")

		if load == None:
			self.__reportTestSkip("no data from monitor plugin available")
		else:
				try:
					_plugin.setTuning(load)
				except Exception as e:
					self.__reportTestResult(e)
					return False
				self.__reportTestResult()

		# cleanup()

		self.__reportTestStep("call cleanup()")
		try:
			_plugin.cleanup()
		except Exception as e:
			self.__reportTestResult(e)
			return False
		self.__reportTestResult()

		return True

