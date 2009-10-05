# Copyright (C) 2008, 2009 Red Hat, Inc.
# Authors: Phil Knirsch
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

import time,os,sys,locale,ConfigParser

class Tuned:
	def __init__(self):
		self.interval = 10
		self.mp = []
		self.tp = []

	def __initplugins__(self, path, module, store):
		_files = map(lambda v: v[:-3], filter(lambda v: v[-3:] == ".py" and \
                             v != "__init__.py" and \
                             v[0] != '.', \
                             os.listdir(path+"/"+module)))
		locale.setlocale(locale.LC_ALL, "C")
		_files.sort()
		locale.setlocale(locale.LC_ALL, "")
		for _i in _files:
			_cmd = "from %s.%s import _plugin" % (module, _i)
    			exec _cmd
			store.append(_plugin)

	def init(self, path, cfgfile):
		self.config = ConfigParser.RawConfigParser()
		self.config.read(cfgfile)

		if not self.config.has_section("main"):
			self.config.add_section("main")

		if self.config.has_option("main", "interval"):
			self.interval = self.config.getint("main", "interval")
		else:
			self.config.set("main", "interval", self.interval)
		if self.config.has_option("main", "pidfile"):
			self.pidfile = self.config.get("main", "pidfile")
		else:
			self.pidfile = "/var/run/tuned.pid"
		self.__initplugins__(path, "monitorplugins", self.mp)
		self.__initplugins__(path, "tuningplugins", self.tp)
		for p in self.mp:
			p.init(self.config)
		for p in self.tp:
			p.init(self.config)

	def run(self):
		try:
			f = open(self.pidfile, "w")
			f.write("%d" % os.getpid())
			f.close()
		except:
			print >>sys.stderr, "Can't write to pidfile", self.pidfile;
		print("Running...")
		while True:
			lh = {}
			for p in self.mp:
				lh.update(p.getLoad())
			for p in self.tp:
				p.setTuning(lh)
			time.sleep(self.interval)

	def cleanup(self, signum=0, frame=None):
		print("Cleanup...")
		for p in self.mp:
			p.cleanup()
		for p in self.tp:
			p.cleanup()
		try:
			os.unlink(self.pidfile)
		except:
			print >>sys.stderr, "can't remove pidfile", self.pidfile;

tuned = Tuned()
