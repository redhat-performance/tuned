import re

class CPUInfoLibrary(object):
        def __init__(self, file_handler):
                self._file_handler = file_handler

        def cpuinfo_match(self, args):
                try:
                        cpuinfo = self._file_handler.read("/proc/cpuinfo")
                except IOError:
                        cpuinfo = ""
                for i in range(0, len(args), 2):
                        if i + 1 < len(args):
                                if re.search(args[i], cpuinfo, re.MULTILINE):
                                        return args[i + 1]
                if len(args) % 2:
                        return args[-1]
                else:
                        return ""
