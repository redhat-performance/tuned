import tuned.patterns
import tuned.logs
import tuned.utils
import tuned.commands
import tuned.commands.exception
import tuned.utils.storage

log = tuned.logs.get()

class CommandRepository(tuned.patterns.Singleton):
	def __init__(self):
		super(self.__class__, self).__init__()
		self._loader = tuned.utils.PluginLoader("tuned.commands", "command_", tuned.plugins.Command)
		self._commands = {}

	def execute(self, command_name, args):
		# Load command on-the-fly
		if not self._commands.has_key(command_name):
			self._load_command(command_name)

		# Execute command and get the previously set values.
		log.debug("executing command %s with args %s" % (command_name, unicode(args)))
		previous_args = self._commands[command_name].execute(args)

		# Store the previously set values
		storage = tuned.utils.storage.Storage.get_instance()
		storage.data[command_name] = previous_args
		storage.save()

	def _load_command(self, command_name)
		log.debug("loading command %s" % command_name)
		try:
			command_cls = self._loader.load(command_name)
			command_instance = command_cls()
			self._commands[command_instance.name](command_instance)
			return command_instance
		except Exception as exception:
			command_exception = tuned.plugins.exception.LoadCommandException(command_name, exception)
			raise command_exception

	def delete(self, command_name):
		log.debug("removing command %s" % command_name)
		del self._commands[command_name]
