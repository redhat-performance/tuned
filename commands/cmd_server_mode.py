# -*- coding: utf-8 -*-


from kobo.cli import Command
import os

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
        # call ktune - need check of status
        os.system('service ktune start')
        # usb suspend?

