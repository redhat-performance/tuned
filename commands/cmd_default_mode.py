# -*- coding: utf-8 -*-

import os
import glob
import kobo.shortcuts
from kobo.cli import Command

class Default(Command):
    """star ktune and tuned with default settings"""
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
        os.system('service ktune start')
        os.system('chkconfig --add ktune && chkconfig --level 345 ktune on')
        os.system('service tuned start')
        os.system('chkconfig --add tuned && chkconfig --level 345 tuned on')

#        usb_devices = glob.glob('/sys/bus/usb/devices/?-?/')
#        for i in usb_devices:
#		retcode, output = kobo.shortcuts.run('echo 2 > %spower/autosuspend' % i)
#		retcode, output = kobo.shortcuts.run('echo auto > %spower/level' % i)