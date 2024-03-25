import re
import tuned.logs
from tuned.utils.config_parser import ConfigParser, Error
from tuned.exceptions import TunedException
import tuned.consts as consts
from tuned.utils.commands import commands

__all__ = ["GlobalConfig"]

log = tuned.logs.get()

class GlobalConfig():

	def __init__(self,config_file = consts.GLOBAL_CONFIG_FILE):
		self._cfg = {}
		self.load_config(file_name=config_file)
		self._cmd = commands()

	@staticmethod
	def get_global_config_spec():
		"""
		Easy validation mimicking configobj
		Returns two dicts, first with default values (default None)
		global_default[consts.CFG_SOMETHING] = consts.CFG_DEF_SOMETHING or None
		second with configobj function for value type (default "get" for string, others eg getboolean, getint)
		global_function[consts.CFG_SOMETHING] = consts.CFG_FUNC_SOMETHING or get
		}
		"""
		options = [opt for opt in dir(consts)
				   if opt.startswith("CFG_") and
				   not opt.startswith("CFG_FUNC_") and
				   not opt.startswith("CFG_DEF_")]
		global_default = dict((getattr(consts, opt), getattr(consts, "CFG_DEF_" + opt[4:], None)) for opt in options)
		global_function = dict((getattr(consts, opt), getattr(consts, "CFG_FUNC_" + opt[4:], "get")) for opt in options)
		return global_default, global_function

	def load_config(self, file_name = consts.GLOBAL_CONFIG_FILE):
		"""
		Loads global configuration file.
		"""
		log.debug("reading and parsing global configuration file '%s'" % file_name)
		try:
			config_parser = ConfigParser(delimiters=('='), inline_comment_prefixes=('#'), strict=False)
			config_parser.optionxform = str
			with open(file_name) as f:
				config_parser.read_string("[" + consts.MAGIC_HEADER_NAME + "]\n" + f.read(), file_name)
			self._cfg, _global_config_func = self.get_global_config_spec()
			for option in config_parser.options(consts.MAGIC_HEADER_NAME):
				if option in self._cfg:
					try:
						func = getattr(config_parser, _global_config_func[option])
						self._cfg[option] = func(consts.MAGIC_HEADER_NAME, option)
					except Error:
						raise TunedException("Global TuneD configuration file '%s' is not valid."
											 % file_name)
				else:
					log.info("Unknown option '%s' in global config file '%s'." % (option, file_name))
					self._cfg[option] = config_parser.get(consts.MAGIC_HEADER_NAME, option, raw=True)
		except IOError as e:
			raise TunedException("Global TuneD configuration file '%s' not found." % file_name)
		except Error as e:
			raise TunedException("Error parsing global TuneD configuration file '%s'." % file_name)

	def get(self, key, default = None):
		return self._cfg.get(key, default)

	def get_bool(self, key, default = None):
		if self._cmd.get_bool(self.get(key, default)) == "1":
			return True
		return False

	def get_int(self, key, default = 0):
		i = self._cfg.get(key, default)
		if i:
			if isinstance(i, int):
				return i
			else:
				return int(i, 0)
		return default

	def get_list(self, key, default = []):
		value = self._cfg.get(key, default)
		if isinstance(value, list):
			return value
		if value.strip() == "":
			return []
		return [x.strip() for x in re.split(r",|;", value)]

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
