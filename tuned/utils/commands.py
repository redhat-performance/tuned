import tuned.logs
import copy
import os
import tuned.consts as consts
from configobj import ConfigObj
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
		rc = True
	except (OSError,IOError) as e:
		rc = False
		log.error("Writing to file %s error: %s" % (f, e))
	return rc

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
	retcode = None
	if not hasattr(execute, "_environment"):
		execute._environment = os.environ.copy()
		execute._environment["LC_ALL"] = "C"

	log.debug("Executing %s." % str(args))
	out = ""
	try:
		proc = Popen(args, stdout=PIPE, stderr=PIPE, env=execute._environment, close_fds=True)
		out, err = proc.communicate()

		retcode = proc.returncode
		if retcode:
			err_out = err[:-1]
			if len(err_out) == 0:
				err_out = out[:-1]
			log.error("Executing %s error: %s" % (args[0], err_out))
	except (OSError,IOError) as e:
		retcode = -1
		log.error("Executing %s error: %s" % (args[0], e))
	return retcode, out

# Helper for parsing kernel options like:
# [always] never
# It will return 'always'
def get_active_option(options, dosplit = True):
	m = re.match(r'.*\[([^\]]+)\].*', options)
	if m:
		return m.group(1)
	if dosplit:
		return options.split()[0]
	return options

def recommend_profile():
	profile = consts.DEFAULT_PROFILE
	for f in consts.LOAD_DIRECTORIES:
		config = ConfigObj(os.path.join(f, consts.AUTODETECT_FILE))
		for section in reversed(config.keys()):
			match1 = match2 = True
			for option in config[section].keys():
				value = config[section][option]
				if value == "":
					value = r"^$"
				if option == "virt":
#					print "ddd" + execute("virt-what")[1]
					if not re.match(value, execute("virt-what")[1], re.S):
						match1 = False
				elif option == "system":
					if not re.match(value, read_file(consts.SYSTEM_RELEASE_FILE), re.S):
						match2 = False
			if match1 and match2:
				profile = section
	return profile
