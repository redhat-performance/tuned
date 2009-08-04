# -*- coding: utf-8 -*-

import os
import os.path
import glob
import kobo.shortcuts
from kobo.cli import Command

class Modes(Command):
    """set mode"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s" % self.normalized_name

        self.parser.add_option(
            "--show-disabled",
            default=False,
            action="store_true",
            help="show disabled workers"
        )


    def run(self, *args, **kwargs):
        # link config files into directory which is exectued by ktune
	enablektune = False
	enabletuned = False
	if len(args) == 0:
		return
        if os.path.exists("/etc/tune-profiles/"):
		os.system('service ktune stop')
	        os.system('chkconfig --add ktune && chkconfig --level 345 ktune off')
        	os.system('service tuned stop')
        	os.system('chkconfig --add tuned && chkconfig --level 345 tuned off')
                modes = os.listdir("/etc/tune-profiles")
                if modes > 0:
                        print 'Mode %s' % args[0]
			if os.path.exists('/etc/ktune.d/tunedadm.sh'):
				os.remove('/etc/ktune.d/tunedadm.sh')
			if os.path.exists('/etc/ktune.d/tunedadm.conf'):
				os.remove('/etc/ktune.d/tunedadm.conf')
                        file = ('/etc/tune-profiles/%s/ktune.sysconfig' % args[0])
			if os.path.exists(file):
				enablektune = True
                        	os.rename('/etc/sysconfig/ktune', '/etc/sysconfig/ktune.bckp')
                        	os.symlink(file, '/etc/sysconfig/ktune')
                        file = ('/etc/tune-profiles/%s/ktune.sh' % args[0])
			if os.path.exists(file):
                        	os.symlink(file, '/etc/ktune.d/tunedadm.sh')
			file = ('/etc/tune-profiles/%s/sysctl.ktune' % args[0])
			if os.path.exists(file):
				os.symlink(file, '/etc/ktune.d/tunedadm.conf')
                        file = ('/etc/tune-profiles/%s/tuned.conf' % args[0])
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
