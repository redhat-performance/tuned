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
        if os.path.exists("/etc/tune-profiles/"):
                modes = os.listdir("/etc/tune-profiles")
                if modes > 0:
                        print 'Mode %s' % args[0]
                        file1 = ('/etc/tune-profiles/%s/ktune.conf' % args[0])
                        os.symlink(file1, '/etc/ktune.d/ktune.conf')
                        file2 = ('/etc/tune-profiles/%s/ktune.sh' % args[0])
                        os.symlink(file2, '/etc/ktune.d/ktune.sh')
                        os.rename('/etc/tuned.conf', '/etc/tuned.conf.bckp')
                        file3 = ('/etc/tune-profiles/%s/tuned.conf' % args[0])
                        os.symlink(file3, '/etc/tuned.conf')
                        #if os.path.exists("/etc/tune-profiles/server/ktune"):
                        os.rename('/etc/sysconfig/ktune', '/etc/sysconfig/ktune.bckp')
                        file4 = ('/etc/tune-profiles/%s/ktune' % args[0])
                        os.symlink(file4, '/etc/sysconfig/ktune')

        os.system('service ktune start')
        os.system('chkconfig --add ktune && chkconfig --level 345 ktune on')

        os.system('service tuned start --config=/etc/tune-profiles/server/tuned.conf')
        os.system('chkconfig --add tuned && chkconfig --level 345 tuned on')