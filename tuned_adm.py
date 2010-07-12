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

import sys
import os
import os.path
import glob

class Tuned_adm:

	def __init__(self, profile_dir = "/etc/tune-profiles"):
		self.profile_dir = os.path.normpath(profile_dir)
		self.active_file = os.path.join(profile_dir, "active-profile")

	def error(self, msg, exit_code = 1):
		print >>sys.stderr, msg
		sys.exit(exit_code)

	def check_permissions(self):
		if not os.getuid() == 0:
			self.error("Only root can run this script.", 2)

	def run(self, args):
		if args[0] == "list":
			self.list()
		elif args[0] == "active":
			self.active()
		elif args[0] == "off":
			self.check_permissions()
			self.off()
		elif args[0] == "profile":
			if len(args) == 2:
				self.check_permissions()
				self.profile(args[1])
			else:
				self.error("Invalid profile specification. Use 'tuned-adm list' to get all available profiles.")
		else:
			self.error("Nonexistent argument '%s'." % args[0])

	def list(self):
		modes = os.listdir(self.profile_dir)
		if len(modes) > 0:
			print "Available profiles:"
			for mode in modes:
				dir = os.path.join(self.profile_dir, mode)
				if not os.path.isdir(dir):
					continue
				print "- %s" % mode

			self.active()
		else:
			print "No profiles defined."

	def active(self):
		print "Current active profile: %s" % self.get_active()

	def get_active(self):
		file = open(self.active_file, "r")
		profile = file.read()
		file.close()
		return profile

	def set_active(self, profile):
		file = open(self.active_file, "w")
		file.write(profile)
		file.close()

	def verify_profile(self, profile):
		path = os.path.abspath(os.path.join(self.profile_dir, profile))

		if not path.startswith("%s/" % self.profile_dir):
			return False

		if not os.path.isdir(path):
			return False

		return True

	def remove(self, wildcard, filter = None):
		if filter == None:
			filter = lambda file: True

		files = glob.glob(wildcard)
		for f in files:
			if filter(f):
				os.unlink(f)

	def off(self):
		self.set_active("off")

		# remove profile settings
		self.remove("/etc/ktune.d/*.conf", os.path.islink)
		self.remove("/etc/ktune.d/*.sh", os.path.islink)

		# restore previous ktune settings (if present)
		if os.path.exists("/etc/sysconfig/ktune.bckp"):
			os.rename("/etc/sysconfig/ktune.bckp", "/etc/sysconfig/ktune")
		if os.path.exists("/etc/tuned.conf.bckp") and os.path.exists("/etc/tuned.conf"):
			os.rename("/etc/tuned.conf.bckp", "/etc/tuned.conf")

		# disable services
		os.system('service ktune stop')
		os.system('service tuned stop')
		os.system('chkconfig --del ktune')
		os.system('chkconfig --del tuned')

	def profile(self, profile):
		enablektune = False
		enabletuned = False

		if not self.verify_profile(profile):
			self.error("Invalid profile. Use 'tuned-adm list' to get all available profiles.")

		profile_root = os.path.join(self.profile_dir, profile)

		# disabling services

		os.system('service ktune stop')
		os.system('service tuned stop')
		os.system('chkconfig --add ktune && chkconfig --level 345 ktune off')
		os.system('chkconfig --add tuned && chkconfig --level 345 tuned off')

		print >>sys.stderr, "Switching to profile '%s'" % profile
		self.set_active(profile)

		# ktune settings

		self.remove('/etc/ktune.d/tunedadm.sh')
		self.remove('/etc/ktune.d/tunedadm.conf')

		file = os.path.join(profile_root, "ktune.sysconfig")
		if os.path.isfile(file):
			enablektune = True
			os.rename('/etc/sysconfig/ktune', '/etc/sysconfig/ktune.bckp')
			os.symlink(file, '/etc/sysconfig/ktune')

		file = os.path.join(profile_root, 'ktune.sh')
		if os.path.isfile(file):
			os.symlink(file, '/etc/ktune.d/tunedadm.sh')

		file = os.path.join(profile_root, 'sysctl.ktune')
		if os.path.isfile(file):
			os.symlink(file, '/etc/ktune.d/tunedadm.conf')

		# tuned settings

		file = os.path.join(profile_root, 'tuned.conf')
		if os.path.isfile(file):
			enabletuned = True
			os.rename('/etc/tuned.conf', '/etc/tuned.conf.bckp')
			os.symlink(file, '/etc/tuned.conf')

		# enabling services

		if enablektune:
			os.system('service ktune start')
			os.system('chkconfig --add ktune && chkconfig --level 345 ktune on')

		if enabletuned:
			os.system('service tuned start')
			os.system('chkconfig --add tuned && chkconfig --level 345 tuned on')

tuned_adm = Tuned_adm()
