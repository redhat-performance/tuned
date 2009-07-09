#!/usr/bin/python

import os
import sys
import locale
from kobo.cli import *


from kobo.tback import *
set_except_hook()


import commands
CommandContainer.register_module(commands)


def main(argv):
    parser = CommandOptionParser(command_container=CommandContainer(), default_command="help")
    parser.run()

if __name__ == "__main__":
    main(sys.argv[1:])
