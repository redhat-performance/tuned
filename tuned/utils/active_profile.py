import errno

import tuned.consts as consts
from tuned.utils.file import FileHandler
from tuned.exceptions import TunedException

class ActiveProfileManager(object):
	def __init__(self, file_handler = FileHandler()):
		self._file_handler = file_handler

	def get(self):
		profile_name = ""
		mode = ""
		try:
			profile_name = self._file_handler.read(
					consts.ACTIVE_PROFILE_FILE)
			profile_name = profile_name.strip()
		except IOError as e:
			if e.errno != errno.ENOENT:
				raise TunedException("Failed to read active profile: %s" % e)
		try:
			mode = self._file_handler.read(consts.PROFILE_MODE_FILE)
			mode = mode.strip()
			if mode not in ["", consts.ACTIVE_PROFILE_AUTO, consts.ACTIVE_PROFILE_MANUAL]:
				raise TunedException("Invalid value in file %s." % consts.PROFILE_MODE_FILE)
		except IOError as e:
			if e.errno != errno.ENOENT:
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
			if profile_name is None:
				value = ""
			else:
				value = profile_name + "\n"
			self._file_handler.write(consts.ACTIVE_PROFILE_FILE, value)
		except (OSError,IOError) as e:
			raise TunedException("Failed to save active profile: %s" % e.strerror)
		try:
			mode = consts.ACTIVE_PROFILE_MANUAL if manual else consts.ACTIVE_PROFILE_AUTO
			self._file_handler.write(consts.PROFILE_MODE_FILE,
					mode + "\n")
		except (OSError,IOError) as e:
			raise TunedException("Failed to save profile mode: %s" % e.strerror)
