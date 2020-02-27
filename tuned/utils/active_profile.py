import errno

import tuned.consts as consts
from tuned.exceptions import TunedException

class ActiveProfileManager(object):
	def get(self):
		profile_name = ""
		mode = ""
		try:
			with open(consts.ACTIVE_PROFILE_FILE, "r") as f:
				profile_name = f.read().strip()
		except IOError as e:
			if e.errno != errno.ENOENT:
				raise TunedException("Failed to read active profile: %s" % e)
		except (OSError, EOFError) as e:
			raise TunedException("Failed to read active profile: %s" % e)
		try:
			with open(consts.PROFILE_MODE_FILE, "r") as f:
				mode = f.read().strip()
				if mode not in ["", consts.ACTIVE_PROFILE_AUTO, consts.ACTIVE_PROFILE_MANUAL]:
					raise TunedException("Invalid value in file %s." % consts.PROFILE_MODE_FILE)
		except IOError as e:
			if e.errno != errno.ENOENT:
				raise TunedException("Failed to read profile mode: %s" % e)
		except (OSError, EOFError) as e:
			raise TunedException("Failed to read profile mode: %s" % e)
		if mode == "":
			manual = None
		else:
			manual = mode == consts.ACTIVE_PROFILE_MANUAL
		if profile_name == "":
			profile_name = None
		return (profile_name, manual)

	def save(self, profile_name, manual):
		try:
			with open(consts.ACTIVE_PROFILE_FILE, "w") as f:
				if profile_name is not None:
					f.write(profile_name + "\n")
		except (OSError,IOError) as e:
			raise TunedException("Failed to save active profile: %s" % e.strerror)
		try:
			with open(consts.PROFILE_MODE_FILE, "w") as f:
				mode = consts.ACTIVE_PROFILE_MANUAL if manual else consts.ACTIVE_PROFILE_AUTO
				f.write(mode + "\n")
		except (OSError,IOError) as e:
			raise TunedException("Failed to save profile mode: %s" % e.strerror)
