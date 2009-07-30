# -*- coding: utf-8 -*-

import os
import os.path
import glob
import kobo.shortcuts
from kobo.cli import Command

class List(Command):
    """list of modes"""
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
	        if len(modes) > 0:
                        print "Modes: "
	                for i in range(len(modes)):
	                        print modes[i]
	        else:
	                print "No other profiles than default defined."
