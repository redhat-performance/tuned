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

import os, sys, re
from logging import log
from streamcapture import capture

class AdmTester:

	def __init__(self):
		self.profiles_dir = os.path.normpath(os.path.dirname(__file__) + "/../tune-profiles")
		self.profiles_fake_dir = os.path.normpath(os.path.dirname(__file__) + "/fake-profiles")

	def run(self):
		import tuned_adm
		self.tuned_adm = tuned_adm.tuned_adm

		self.tuned_adm.init(self.profiles_dir)

		self.__check_profiles()
		self.__check_privileges()

		# profiles switching
		self.tuned_adm.init(self.profiles_fake_dir)

		testing_states = [
			#[ None, False, False ], # off mode
			[ "enabled-all", True, True ],
			[ None, False, False ], # off mode
			[ "enabled-tuned", True, False ],
			[ "enabled-ktune", False, True ],
			[ "disabled-all", False, False ],
			[ "disabled-config", True, False ]
		]

		for ts in testing_states:
			self.__check_state(ts[0], ts[1], ts[2])

	def __check_profiles(self):
		log.test("profiles listing")

		profiles_tester = os.listdir(self.profiles_dir)
		profiles_tester = filter(lambda f: f[0] != ".", profiles_tester)

		try:
			capture.clean()
			capture.capture()
			self.tuned_adm.run(["list"])
			capture.stdout()
		except Exception as e:
			log.report_e(e)
			return False

		# printed profiles (first line "Modes:" is skipped)
		profiles_tuned = capture.getcaptured().splitlines()[1:]

		# compare profiles_tester and profiles_tuned

		error = False
		for p in profiles_tester:
			if not p in profiles_tuned:
				log.info("tune-adm does not report profile '%s'" % p)
				error = True

		for p in profiles_tuned:
			if not p in profiles_tester:
				log.info("tune-adm reports extra profile '%s'" % p)
				error = True

		if error:
			log.result("profiles detected by this test differ from these reported by tuned-adm")
		else:
			log.result()
		
		return True

	def __check_privileges(self):
		log.test("privileges")
		if os.getuid() != 0:
			log.result("You have to be root to run all following tests.")
			return False
		else:
			log.result()
			return True

	def __service_running(self, service):
		status = os.system("service %s status 1>/dev/null 2>&1" % service)
		# 0 running, 3 stopped
		if status == 0:
			return True
		else:
			return False

	def __initscript_enabled(self, service):
		if os.system('chkconfig | grep -qx "^%s\W.*on.*$"' % service) == 0:
			return True
		else:
			return False

	def __check_state(self, profile, tuned_running, ktune_running):
		is_ok = True

		if profile == None:
			self.tuned_adm.run(["off"])
			log.test("checking state: off")
		else:
			self.tuned_adm.run(["profile", profile])
			log.test("checking state: %s" % profile)

		log.indent()

		# services status

		log.test("service 'tuned'")
		if self.__service_running("tuned") == tuned_running:
			log.result()
		else:
			is_ok = False
			log.result("should %s" % ( "be running" if tuned_running else "not be running" ))

		log.test("service 'ktune'")
		if self.__service_running("ktune") == ktune_running:
			log.result()
		else:
			is_ok = False
			log.result("should %s" % ( "be running" if ktune_running else "not be running" ))

		# init scripts

		log.test("checking 'tuned' initscript")
		if self.__initscript_enabled("tuned") == tuned_running:
			log.result()
		else:
			is_ok = False
			log.result("%s be enabled" % ( "should" if tuned_running else "should not" ))

		log.test("checking 'ktune' initscript")
		if self.__initscript_enabled("ktune") == ktune_running:
			log.result()
		else:
			is_ok = False
			log.result("%s be enabled" % ( "should" if ktune_running else "should not" ))

		# config files

		want_tunedadm_sh = False
		want_tunedadm_conf = False

		if profile != None:
			want_tunedadm_sh = os.path.exists("%s/%s/ktune.sh" % (self.profiles_fake_dir, profile))
			want_tunedadm_conf = os.path.exists("%s/%s/sysctl.ktune" % (self.profiles_fake_dir, profile))

		log.test("checking '/etc/ktune.d/tunedadm.sh'")
		if want_tunedadm_sh == os.path.exists("/etc/ktune.d/tunedadm.sh"):
			log.result()
		else:
			is_ok = False
			log.result("file should %s" % ( "exist" if want_tunedadm_sh else "not exist" ))

		log.test("checking '/etc/ktune.d/tunedadm.conf'")
		if want_tunedadm_conf == os.path.exists("/etc/ktune.d/tunedadm.conf"):
			log.result()
		else:
			is_ok = False
			log.result("file should %s" % ( "exist" if want_tunedadm_conf else "not exist" ))

		log.unindent()
		return is_ok

