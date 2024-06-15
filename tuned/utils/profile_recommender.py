import os
import re
import errno
import procfs
import subprocess
from tuned.utils.config_parser import ConfigParser, Error

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

	def __init__(self, is_hardcoded = False):
		self._is_hardcoded = is_hardcoded
		self._commands = commands()
		self._chassis_type = None

	def recommend(self):
		profile = consts.DEFAULT_PROFILE
		if self._is_hardcoded:
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
		syspurpose_error_logged = False
		try:
			if not os.path.isfile(fname):
				return None
			config = ConfigParser(delimiters=('='), inline_comment_prefixes=('#'), strict=False)
			config.optionxform = str
			with open(fname) as f:
				config.read_file(f, fname)
			for section in config.sections():
				match = True
				for option in config.options(section):
					value = config.get(section, option, raw=True)
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
								consts.SYSTEM_RELEASE_FILE,
								no_error = True), re.S):
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
						chassis_type = self._get_chassis_type()

						if not re.match(value, chassis_type, re.IGNORECASE):
							match = False
					elif option == "syspurpose_role":
						role = ""
						if have_syspurpose:
							s = syspurpose.files.SyspurposeStore(
									syspurpose.files.USER_SYSPURPOSE,
									raise_on_error = True)
							try:
								s.read_file()
								role = s.contents["role"]
							except (IOError, OSError, KeyError) as e:
								if hasattr(e, "errno") and e.errno != errno.ENOENT:
									log.error("Failed to load the syspurpose\
										file: %s" % e)
						else:
							if not syspurpose_error_logged:
								log.error("Failed to process 'syspurpose_role' in '%s'\
									, the syspurpose module is not available" % fname)
								syspurpose_error_logged = True
						if re.match(value, role, re.IGNORECASE) is None:
							match = False

				if match:
					# remove the ",.*" suffix
					r = re.compile(r",[^,]*$")
					matching_profile = r.sub("", section)
					break
		except (IOError, OSError, Error) as e:
			log.error("error processing '%s', %s" % (fname, e))
		return matching_profile

	def _get_chassis_type(self):
		if self._chassis_type is not None:
			log.debug("returning cached chassis type '%s'" % self._chassis_type)
			return self._chassis_type

		# Check DMI sysfs first
		# Based on SMBios 3.3.0 specs (https://www.dmtf.org/sites/default/files/standards/documents/DSP0134_3.3.0.pdf)
		DMI_CHASSIS_TYPES = ["", "Other", "Unknown", "Desktop", "Low Profile Desktop", "Pizza Box", "Mini Tower", "Tower",
							"Portable", "Laptop", "Notebook", "Hand Held", "Docking Station", "All In One", "Sub Notebook",
							"Space-saving", "Lunch Box", "Main Server Chassis", "Expansion Chassis", "Sub Chassis",
							"Bus Expansion Chassis", "Peripheral Chassis", "RAID Chassis", "Rack Mount Chassis", "Sealed-case PC",
							"Multi-system", "CompactPCI", "AdvancedTCA", "Blade", "Blade Enclosing", "Tablet",
							"Convertible", "Detachable", "IoT Gateway", "Embedded PC", "Mini PC", "Stick PC"]
		try:
			with open('/sys/devices/virtual/dmi/id/chassis_type', 'r') as sysfs_chassis_type:
				chassis_type_id = int(sysfs_chassis_type.read())

			self._chassis_type = DMI_CHASSIS_TYPES[chassis_type_id]
		except IndexError:
			log.error("Unknown chassis type id read from dmi sysfs: %d" % chassis_type_id)
		except (OSError, IOError) as e:
			log.warning("error accessing dmi sysfs file: %s" % e)

		if self._chassis_type:
			log.debug("chassis type - %s" % self._chassis_type)
			return self._chassis_type

		# Fallback - try parsing dmidecode output
		try:
			p_dmi = subprocess.Popen(['dmidecode', '-s', 'chassis-type'],
				stdout=subprocess.PIPE, stderr=subprocess.PIPE,
				close_fds=True)

			(dmi_output, dmi_error) = p_dmi.communicate()

			if p_dmi.returncode:
				log.error("dmidecode finished with error (ret %d): '%s'" % (p_dmi.returncode, dmi_error))
			else:
				self._chassis_type = dmi_output.strip().decode()
		except (OSError, IOError) as e:
			log.warning("error executing dmidecode tool : %s" % e)

		if not self._chassis_type:
			log.debug("could not determine chassis type.")
			self._chassis_type = ""
		else:
			log.debug("chassis type - %s" % self._chassis_type)

		return self._chassis_type
