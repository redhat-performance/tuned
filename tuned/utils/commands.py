import tuned.logs
import copy
import os
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
	out = ""
	try:
		proc = Popen(args, stdout=PIPE, stderr=PIPE)
		out, err = proc.communicate()

		if proc.returncode:
			log.error("Executing %s error: %s" % (args[0], err[:-1]))
	except (OSError,IOError) as e:
		log.error("Executing %s error: %s" % (args[0], e))
	return out

