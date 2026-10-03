import base
from tuned.utils.commands import commands

class testfunc(base.Function):
    """
    Test function
    """
    def __init__(self):
        super(self.__class__, self).__init__("testfunc", 2)

    def execute(self, args):
        f = open(str(args[0]),'w')
        f.write(str(args[1]))
        f.close()
        return str(args[1]) + 'returned'

