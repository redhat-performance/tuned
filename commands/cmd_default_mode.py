# -*- coding: utf-8 -*-


from kobo.cli import Command
import os

class Default(Command):
    """set default mode"""
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
        os.system('service ktune stop')
	os.system('service tuned stop')

