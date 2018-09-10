import tuned.logs
from configobj import ConfigObj, ConfigObjError
from validate import Validator
from tuned.exceptions import TunedException
import tuned.consts as consts
from tuned.utils.commands import commands

__all__ = ["GlobalConfig"]

log = tuned.logs.get()

class GlobalConfig():

	global_config_spec = ["dynamic_tuning = boolean(default=%s)" % consts.CFG_DEF_DYNAMIC_TUNING,
		"sleep_interval = integer(default=%s)" % consts.CFG_DEF_SLEEP_INTERVAL,
		"update_interval = integer(default=%s)" % consts.CFG_DEF_UPDATE_INTERVAL,
		"recommend_command = boolean(default=%s)" % consts.CFG_DEF_RECOMMEND_COMMAND]

	def __init__(self,config_file = consts.GLOBAL_CONFIG_FILE):
		self._cfg = {}
		self.load_config(file_name=config_file)
		self._cmd = commands()

	def load_config(self, file_name = consts.GLOBAL_CONFIG_FILE):
		"""
		Loads global configuration file.
		"""
		log.debug("reading and parsing global configuration file '%s'" % file_name)
		try:
			self._cfg = ConfigObj(file_name, configspec = self.global_config_spec, raise_errors = True, \
				file_error = True, list_values = False, interpolation = False)
		except IOError as e:
			raise TunedException("Global tuned configuration file '%s' not found." % file_name)
		except ConfigObjError as e:
			raise TunedException("Error parsing global tuned configuration file '%s'." % file_name)
		vdt = Validator()
		if (not self._cfg.validate(vdt, copy=True)):
			raise TunedException("Global tuned configuration file '%s' is not valid." % file_name)

	def get(self, key, default = None):
		return self._cfg.get(key, default)

	def get_bool(self, key, default = None):
		if self._cmd.get_bool(self.get(key, default)) == "1":
			return True
		return False

	def set(self, key, value):
		self._cfg[key] = value

	def get_size(self, key, default = None):
		val = self.get(key)
		if val is None:
			return default
		ret = self._cmd.get_size(val)
		if ret is None:
			log.error("Error parsing value '%s', using '%s'." %(val, default))
			return default
		else:
			return ret
