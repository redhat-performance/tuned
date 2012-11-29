import tuned.logs
import copy
import os
import tuned.consts as consts
import ConfigParser
import re
from subprocess import *

__all__ = ["write_to_file", "read_file", "execute"]

log = tuned.logs.get()

def write_to_file(f, data):
	log.debug("Writing to file: %s < %s" % (f, data))
	try:
		fd = open(f, "w")
		fd.write(str(data))
		fd.close()
	except (OSError,IOError) as e:
		log.error("Writing to file %s error: %s" % (f, e))

def read_file(f):
	old_value = ""
	try:
		f = open(f, "r")
		old_value = f.read()
		f.close()
	except (OSError,IOError) as e:
		log.error("Reading %s error: %s" % (f, e))
	return old_value
	

def execute(args):
	log.debug("Executing %s." % str(args))
	out = ""
	try:
		proc = Popen(args, stdout=PIPE, stderr=PIPE)
		out, err = proc.communicate()

		if proc.returncode:
			log.error("Executing %s error: %s" % (args[0], err[:-1]))
	except (OSError,IOError) as e:
		log.error("Executing %s error: %s" % (args[0], e))
	return out

def recommend_profile():
	profile = consts.DEFAULT_PROFILE
	for f in consts.LOAD_DIRECTORIES:
		parser = ConfigParser.SafeConfigParser(allow_no_value = False)
		try:
			parser.read(os.path.join(f, consts.AUTODETECT_FILE))
		except:
			continue
		for section in reversed(parser.sections()):
			match1 = match2 = True
			for option, value in parser.items(section):
				value = str(value)
				if value == "":
					value = r"^$"
				if option == "virt":
					if not re.match(value, execute("virt-what"), re.S):
						match1 = False
				elif option == "system":
					if not re.match(value, read_file(consts.SYSTEM_RELEASE_FILE), re.S):
						match2 = False
			if match1 and match2:
				profile = section
	return profile
