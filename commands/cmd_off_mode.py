# -*- coding: utf-8 -*-

import os
import glob
import kobo.shortcuts
from kobo.cli import Command

class Off(Command):
    """switch off all tunning"""
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
	if os.path.exists("/etc/tune.d/*.conf"):
		os.remove("/etc/tune.d/*.conf")
	if os.path.exists("/etc/tune.d/*.sh"):
		os.remove("/etc/tune.d/*.sh")
	if os.path.exists("/etc/sysconfig/ktune.bckp"):
		os.system('mv /etc/sysconfig/ktune.bckp /etc/sysconfig/ktune')
		os.remove("/etc/sysconfig/ktune")
        os.system('service ktune stop')
        os.system('service tuned stop')
        os.system('chkconfig --del ktune')
        os.system('chkconfig --del tuned')
        usb_devices = glob.glob('/sys/bus/usb/devices/?-?/')
        for i in usb_devices:
		retcode, output = kobo.shortcuts.run('echo on > %spower/level' % i)
