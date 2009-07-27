# -*- coding: utf-8 -*-

import os
import os.path
import glob
import kobo.shortcuts
from kobo.cli import Command

class Server(Command):
    """set server mode"""
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
	if os.path.exists("/etc/tune-profiles/server/server.conf"):
		os.symlink("/etc/tune-profiles/server/server.conf", "/etc/tune.d/server.conf")
	if os.path.exists("/etc/tune-profiles/server/server.sh"):
		os.symlink("/etc/tune-profiles/server/server.sh", "/etc/tune.d/server.sh")
		os.system('mv /etc/sysconfig/ktune /etc/sysconfig/ktune.bckp')
	if os.path.exists("/etc/tune-profiles/server/ktune"):
		os.symlink("/etc/tune-profiles/server/ktune", "/etc/sysconfig/ktune")
        os.system('service ktune start')
        os.system('chkconfig --add ktune && chkconfig --level 345 ktune on')

        os.system('service tuned start --config=/etc/tune-profiles/server/tuned.conf')
        os.system('chkconfig --add tuned && chkconfig --level 345 tuned on')

        # check all usb-devices in format digit-digit f.e. 1-1
        usb_devices = glob.glob('/sys/bus/usb/devices/?-?/')
        # all usb devices set to auto with 2s idle
        for i in usb_devices:
		retcode, output = kobo.shortcuts.run('echo 2 > %spower/autosuspend' % i)
		retcode, output = kobo.shortcuts.run('echo auto > %spower/level' % i)
