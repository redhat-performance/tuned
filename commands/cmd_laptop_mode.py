# -*- coding: utf-8 -*-


from kobo.cli import Command
import os

class Laptop(Command):
    """laptop mode not implemented yet"""
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
        # this should be part of ktune
        # if on wifi then switch off network card?
        # usb suspend set to auto
        pass
