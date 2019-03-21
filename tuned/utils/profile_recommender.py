import os
import re
import errno
import procfs
import platform
from configobj import ConfigObj, ConfigObjError

have_dmidecode = False
try:
	if (os.geteuid() == 0 and platform.machine() in ["i386", "i486", "i586", "i686", "x86_64"]):
		import dmidecode
		have_dmidecode = True
except:
	pass
try:
	import syspurpose.files
	have_syspurpose = True
except:
	have_syspurpose = False

import tuned.consts as consts
import tuned.logs
from tuned.utils.commands import commands

log = tuned.logs.get()

class ProfileRecommender:

	def __init__(self):
		self._commands = commands()

	def recommend(self, hardcoded = False):
		profile = consts.DEFAULT_PROFILE
		if hardcoded:
			return profile
		has_root = os.geteuid() == 0
		if not has_root:
			log.warning("Profile recommender is running without root privileges. Profiles with virt recommendation condition will be omitted.")
		matching = self.process_config(consts.RECOMMEND_CONF_FILE,
									   has_root=has_root)
		if matching is not None:
			return matching
		files = {}
		for directory in consts.RECOMMEND_DIRECTORIES:
			contents = []
			try:
				contents = os.listdir(directory)
			except OSError as e:
				if e.errno != errno.ENOENT:
					log.error("error accessing %s: %s" % (directory, e))
			for name in contents:
				path = os.path.join(directory, name)
				files[name] = path
		for name in sorted(files.keys()):
			path = files[name]
			matching = self.process_config(path, has_root=has_root)
			if matching is not None:
				return matching
		return profile

	def process_config(self, fname, has_root=True):
		matching_profile = None
		try:
			if not os.path.isfile(fname):
				return None
			config = ConfigObj(fname, list_values = False, interpolation = False)
			for section in list(config.keys()):
				match = True
				for option in list(config[section].keys()):
					value = config[section][option]
					if value == "":
						value = r"^$"
					if option == "virt":
						if not has_root:
							match = False
							break
						if not re.match(value,
								self._commands.execute(["virt-what"])[1], re.S):
							match = False
					elif option == "system":
						if not re.match(value,
								self._commands.read_file(
								consts.SYSTEM_RELEASE_FILE), re.S):
							match = False
					elif option[0] == "/":
						if not os.path.exists(option) or not re.match(value,
								self._commands.read_file(option), re.S):
							match = False
					elif option[0:7] == "process":
						ps = procfs.pidstats()
						ps.reload_threads()
						if len(ps.find_by_regex(re.compile(value))) == 0:
							match = False
					elif option == "chassis_type":
						if have_dmidecode:
							for chassis in dmidecode.chassis().values():
								chassis_type = chassis["data"]["Type"].decode(
										"ascii")
								if re.match(value, chassis_type, re.IGNORECASE):
									break
							else:
								match = False
						else:
							log.debug("Ignoring 'chassis_type' in '%s',\
								dmidecode is not available." % fname)
					elif option == "syspurpose_role":
						if have_syspurpose:
							s = syspurpose.files.SyspurposeStore(
									syspurpose.files.USER_SYSPURPOSE,
									raise_on_error = True)
							role = ""
							try:
								s.read_file()
								role = s.contents["role"]
							except (IOError, OSError, KeyError) as e:
								if hasattr(e, "errno") and e.errno != errno.ENOENT:
									log.error("Failed to load the syspurpose\
										file: %s" % e)
							if re.match(value, role, re.IGNORECASE) is None:
								match = False
						else:
							log.error("Failed to process 'syspurpose_role' in '%s'\
								, the syspurpose module is not available" % fname)

				if match:
					# remove the ",.*" suffix
					r = re.compile(r",[^,]*$")
					matching_profile = r.sub("", section)
					break
		except (IOError, OSError, ConfigObjError) as e:
			log.error("error processing '%s', %s" % (fname, e))
		return matching_profile
