class Singleton(object):
	"""
	Singleton design pattern.
	"""

	_instance = None

	def __init__(self):
		if self.__class__ is Singleton:
			raise TypeError("Cannot instantiate directly.")

	@classmethod
	def get_instance(cls):
		"""Get the class instance."""
		if cls._instance is None:
			cls._instance = cls()
		return cls._instance
