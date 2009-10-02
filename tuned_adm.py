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

import sys,os,glob

class Tuned_adm:
	def __init__(self):
		self.profile_dir = "/etc/tune-profiles/"


	def init(self, profile_dir):
		self.profile_dir = profile_dir


	def run(self, args):
		if   args[0] == "list":
			self.list()
		elif args[0] == "off":
			self.off()
		elif args[0] == "profile":
			self.profile(args[1:])
		else:
			print >>sys.stderr, "Nonexistent argument %s" % args[0]
			return 1


	def list(self):
		if os.path.exists(self.profile_dir):
	        	modes = os.listdir(self.profile_dir)
	        	if len(modes) > 0:
                        	print "Modes: "
	                	for i in range(len(modes)):
	                        	print modes[i]
	        	else:
	                	print "No profiles defined."

	def off(self):
	        os.system("rm -rf /etc/ktune.d/*.conf")
        	os.system("rm -rf /etc/ktune.d/*.sh")
        	if os.path.exists("/etc/sysconfig/ktune.bckp"):
                	os.rename("/etc/sysconfig/ktune.bckp", "/etc/sysconfig/ktune")
        	if os.path.exists("/etc/tuned.conf.bckp") and os.path.exists("/etc/tuned.conf"):
                	os.rename("/etc/tuned.conf.bckp", "/etc/tuned.conf")
        	os.system('service ktune stop')
        	os.system('service tuned stop')
        	os.system('chkconfig --del ktune')
        	os.system('chkconfig --del tuned')


	def profile(self, args):
		enablektune = False
		enabletuned = False
		if len(args) == 0:
			print "No profile given. To list all available profiles please run:"
			print "tuned-adm list"
			return
		if not os.path.exists(self.profile_dir+"/"+args[0]):
			print "No profile with name %s found." % args[0]
			return
	        if os.path.exists(self.profile_dir):
			os.system('service ktune stop')
		        os.system('chkconfig --add ktune && chkconfig --level 345 ktune off')
	        	os.system('service tuned stop')
	        	os.system('chkconfig --add tuned && chkconfig --level 345 tuned off')
	                modes = os.listdir(self.profile_dir)
	                if modes > 0:
	                        print 'Switching to profile %s' % args[0]
				if os.path.exists('/etc/ktune.d/tunedadm.sh'):
					os.remove('/etc/ktune.d/tunedadm.sh')
				if os.path.exists('/etc/ktune.d/tunedadm.conf'):
					os.remove('/etc/ktune.d/tunedadm.conf')
	                        file = ('%s/%s/ktune.sysconfig' % (self.profile_dir, args[0]))
				if os.path.exists(file):
					enablektune = True
	                        	os.rename('/etc/sysconfig/ktune', '/etc/sysconfig/ktune.bckp')
	                        	os.symlink(file, '/etc/sysconfig/ktune')
	                        file = ('%s/%s/ktune.sh' % (self.profile_dir, args[0]))
				if os.path.exists(file):
	                        	os.symlink(file, '/etc/ktune.d/tunedadm.sh')
				file = ('%s/%s/sysctl.ktune' % (self.profile_dir, args[0]))
				if os.path.exists(file):
					os.symlink(file, '/etc/ktune.d/tunedadm.conf')
	                        file = ('%s/%s/tuned.conf' % (self.profile_dir, args[0]))
				if os.path.exists(file):
					enabletuned = True
	                        	os.rename('/etc/tuned.conf', '/etc/tuned.conf.bckp')
	                       		os.symlink(file, '/etc/tuned.conf')
	
		if enablektune:
	        	os.system('service ktune start')
		        os.system('chkconfig --add ktune && chkconfig --level 345 ktune on')
	
		if enabletuned:
	        	os.system('service tuned start')
	        	os.system('chkconfig --add tuned && chkconfig --level 345 tuned on')


tuned_adm = Tuned_adm()
