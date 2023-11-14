# ConfigParser wrapper providing compatibility layer for python 2.7/3

try:
	python3 = True
	import configparser as cp
except ImportError:
	python3 = False
	import ConfigParser as cp
	from StringIO import StringIO
	import re

class Error(cp.Error):
	pass

if python3:

	class ConfigParser(cp.ConfigParser):
		pass

else:

	class ConfigParser(cp.ConfigParser):

		def __init__(self, delimiters=None, inline_comment_prefixes=None, strict=False, *args, **kwargs):
			delims = "".join(list(delimiters))
			# REs taken from the python-2.7 ConfigParser
			self.OPTCRE = re.compile(
				r'(?P<option>[^' + delims + r'\s][^' + delims + ']*)'
				r'\s*(?P<vi>[' + delims + r'])\s*'
				r'(?P<value>.*)$'
			)
			self.OPTCRE_NV = re.compile(
				r'(?P<option>[^' + delims + r'\s][^' + delims + ']*)'
				r'\s*(?:'
				r'(?P<vi>[' + delims + r'])\s*'
				r'(?P<value>.*))?$'
			)
			cp.ConfigParser.__init__(self, *args, **kwargs)
			self._inline_comment_prefixes = inline_comment_prefixes or []
			self._re = re.compile(r"\s+(%s).*" % ")|(".join(list(self._inline_comment_prefixes)))

		def read_string(self, string, source="<string>"):
			sfile = StringIO(string)
			self.read_file(sfile, source)

		def readfp(self, fp, filename=None):
			cp.ConfigParser.readfp(self, fp, filename)
			# remove inline comments
			all_sections = [self._defaults]
			all_sections.extend(self._sections.values())
			for options in all_sections:
				for name, val in options.items():
					options[name] = self._re.sub("", val)

		def read_file(self, f, source="<???>"):
			self.readfp(f, source)
