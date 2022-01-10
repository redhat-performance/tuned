try:
	from configparser import ConfigParser
except ImportError:
	# python2.7 support, remove RHEL-7 support end
	from ConfigParser import ConfigParser

class TuneDConfigParser(ConfigParser, object):
	# Wrapper to support deprecated readfp() on python < 3.2 where read_file() is not available
	def read_file(self, fp, source = None):
		def readline_generator(fp):
			line = fp.readline()
			while line:
				yield line
				line = fp.readline()
		try:
			super(TuneDConfigParser, self).read_file(readline_generator(fp), source)
		except AttributeError:
			self.readfp(fp, source)
