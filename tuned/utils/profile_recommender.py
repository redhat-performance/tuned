import os
import re
import errno
import procfs
import subprocess
try:
	from configparser import ConfigParser, Error
except ImportError:
	# python2.7 support, remove RHEL-7 support end
	from ConfigParser import ConfigParser, Error

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
		try:
			if not os.path.isfile(fname):
				return None
			config = ConfigParser()
			config.optionxform = str
			with open(fname) as f:
				config.readfp(f)
			for section in config.sections():
				log.debug("Checking recommendation for profile '%s'" % section)
				match = True
				for option in config.options(section):
					value = config.get(section, option, raw=True)
					if value == "":
						value = r"^$"
					if option == "virt":
						if not has_root:
							match = False
							break
						output = self._commands.execute(["virt-what"])[1]
						if re.match(value, output, re.S):
							log.debug("virt option '%s' matches 'virt-what' command output '%s'" % (value, output))
						else:
							log.debug("virt option '%s' does not match 'virt-what' command output '%s'" % (value, output))
							match = False
					elif option == "system":
						output = self._commands.read_file(consts.SYSTEM_RELEASE_FILE, no_error = True)
						if re.match(value, output, re.S):
							log.debug("system option '%s' matches content '%s' of '%s' file" %
											(value, output.strip(), consts.SYSTEM_RELEASE_FILE))
						else:
							log.debug("system option '%s' does not match content '%s' of '%s' file" %
											(value, output.strip(), consts.SYSTEM_RELEASE_FILE))
							match = False
					elif option[0] == "/":
						if os.path.exists(option) or not re.match(value,
								self._commands.read_file(option), re.S):
							log.debug("File option '%s' matches content of '%s' file" % (value, option))
						else:
							log.debug("File option '%s' does not match content of '%s' file" % (value, option))
							match = False
					elif option[0:7] == "process":
						ps = procfs.pidstats()
						ps.reload_threads()
						output = ps.find_by_regex(re.compile(value))
						if len(output) == 0:
							log.debug("No process matching option '%s' found" % value)
							match = False
						else:
							log.debug("%s processes matching option '%s' found" % (len(output), value))
					elif option == "chassis_type":
						chassis_type = self._get_chassis_type()

						if re.match(value, chassis_type, re.IGNORECASE):
							log.debug("chassis_type option '%s' matches chassis type '%s'" % (value, chassis_type))
						else:
							log.debug("chassis_type option '%s' does not match chassis type '%s'" % (value, chassis_type))
							match = False
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
							if re.match(value, role, re.IGNORECASE):
								log.debug("syspurpose_role option '%s' matches role '%s'" % (value, role))
							else:
								log.debug("syspurpose_role option '%s' does not match role '%s'" % (value, role))
								match = False
						else:
							log.error("Failed to process 'syspurpose_role' in '%s'\
								, the syspurpose module is not available" % fname)

				if match:
					# remove the ",.*" suffix
					r = re.compile(r",[^,]*$")
					matching_profile = r.sub("", section)
					log.debug("All options matched for profile '%s' from section '%s', applying" % (matching_profile, section))
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
			log.warn("error accessing dmi sysfs file: %s" % e)

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
			log.warn("error executing dmidecode tool : %s" % e)

		if not self._chassis_type:
			log.debug("could not determine chassis type.")
			self._chassis_type = ""
		else:
			log.debug("chassis type - %s" % self._chassis_type)

		return self._chassis_type
