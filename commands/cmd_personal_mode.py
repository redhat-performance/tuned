# -*- coding: utf-8 -*-


import os
import sys
import kobo.shortcuts
from kobo.cli import Command


class Personal(Command):
    """set personal mode"""
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
        # call script with personal setting from /etc/ktune.d/
        if len(args) != 1:
            self.parser.error("Argument missing.")

        name_p = args[0]
        show_disabled = kwargs.pop("show_disabled")

        try:
            # for include two strings into function: % (foo, foo)
            #retcode, output = kobo.shortcuts.run('/etc/ktune.d/%s.sh' % name_p)
            pass
        except RuntimeError, ex:
            print str(ex)
            sys.exit(1)

