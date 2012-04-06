class Command(object):
	"""
	Base class for all commands.

	Commands contain algorithms and system commands to change the tuning on live 
	system and are also able to revert the changes they have done.

	Methods requiring reimplementation:
	 - execute(self, args)
	 - revert(self, args)
	"""
	def __init__(self, name, desc = ""):
		self._name = name
		self._desc = desc

	@property
	def name(self):
		return self._name

	@property
	def desc(self):
		return self._desc

	@desc.setter
	def desc(self, desc):
		self._desc = desc

	def execute(self, args):
		raise NotImplementedError()

	def revert(self, args):
		raise NotImplementedError()
