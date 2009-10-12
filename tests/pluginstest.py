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
from logging import log

class PluginsTester:

	def __init__(self, tunedir):

		self.tunedir = tunedir
		self.mp_dir = "monitorplugins"
		self.tp_dir = "tuningplugins"

		self.config = ConfigParser.RawConfigParser()
		self.config.add_section("main")
		self.config.set("main", "interval", 10)

	def run(self):

		self.__check_plugins()

	def __get_plugins_from_dir(self, dir):

		files = os.listdir(self.tunedir + "/" + dir);
		plugins = filter(lambda f: f[0] != "." and f[-3:] == ".py" and f != "__init__.py", files) 
		plugins = map(lambda f: f[:-3], plugins)
		plugins.sort()

		return plugins

	def __check_plugins(self):

		monitorplugins = self.__get_plugins_from_dir(self.mp_dir)
		tuningplugins = self.__get_plugins_from_dir(self.tp_dir)

		# check plugins availability

		self.__check_sibling_plugins(monitorplugins, tuningplugins)

		# monitor plugins test

		log.test("monitor plugins test")
		if len(monitorplugins) == 0:
			log.result("no plugins found")

		log.indent()

		monitor_results = {}
		for mp in monitorplugins:
			load = self.__test_monitor_plugin(mp)
			monitor_results[mp] = load

		log.unindent()

		# tuning plugins test

		log.test("tunning plugins test")

		if len(tuningplugins) == 0:
			log.result("no plugins found")

		log.indent()

		for tp in tuningplugins:
			try:
				load = monitor_results[tp]
			except:
				load = None
			self.__test_tuning_plugin(tp, load)

		log.unindent()

	def __check_sibling_plugins(self, monitorplugins, tuningplugins):

		ok = True

		log.test("monitor and tuning plugins availability")

		for mp in monitorplugins:
			if tuningplugins.count(mp) != 1:
				ok = False
				log.info("monitor plugin '%s' misses tuning plugin" % mp)

		for tp in tuningplugins:
			if monitorplugins.count(tp) != 1:
				ok = False
				log.info("tuning plugin '%s' misses monitor plugin" % tp)

		if ok:
			log.result()
		else:
			log.result("monitor and tunning plugins do not match")

	def __test_monitor_plugin(self, name):

		log.test("monitor plugin: %s" % name)
		log.indent()

		# initialization

		log.test("initialization")
		try:
			exec "from %s.%s import _plugin" % (self.mp_dir, name)
		except Exception as e:
			log.result_e(e)
			log.unindent()
			return None

		log.result()

		# init()

		log.test("call init()")
		try:
			_plugin.init(self.config)
		except Exception as e:
			log.result_e(e)
			log.unindent()
			return None
		log.result()

		# getLoad()

		log.test("call getLoad()")
		try:
			load = _plugin.getLoad()
			if load == None:
				raise Exception("Plugin returned None as a result.")
		except Exception as e:
			log.result_e(e)
			log.unindent()
			return None
		log.result()

		# cleanup()

		log.test("call cleanup()")
		try:
			_plugin.cleanup()
		except Exception as e:
			log.result_e(e)
			log.unindent()
			return load

		log.result()

		log.unindent()
		return load

	def __test_tuning_plugin(self, name, load):

		log.test("tuning plugin: %s" % name)
		log.indent()

		# initialization

		log.test("initialization")
		try:
			exec "from %s.%s import _plugin" % (self.tp_dir, name)
		except Exception as e:
			log.result_e()
			log.unindent()
			return False
		log.result()

		# init()

		log.test("call init()")
		try:
			_plugin.init(self.config)
		except Exception as e:
			log.result_e(e)
			log.unindent()
			return False
		log.result()

		# setTuning()

		log.test("call setTuning()")

		if load == None:
			log.info("no data from monitor plugin available")
		else:
			try:
				_plugin.setTuning(load)
			except Exception as e:
				log.result_e(e)
				log.unindent()
				return False
			log.result()

		# cleanup()

		log.test("call cleanup()")
		try:
			_plugin.cleanup()
		except Exception as e:
			log.result_e(e)
			log.unindent()
			return False
		log.result()

		log.unindent()
		return True

