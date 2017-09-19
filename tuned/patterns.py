from threading import Lock

class Singleton(object):
	"""
	Singleton design pattern.
	"""

	_instance = None
	_lock = Lock()

	def __init__(self):
		if self.__class__ is Singleton:
			raise TypeError("Cannot instantiate directly.")

	@classmethod
	def get_instance(cls):
		"""Get the class instance."""
		if cls._instance is not None:
			return cls._instance
		cls._lock.acquire()
		if cls._instance is None:
			cls._instance = cls()
		cls._lock.release()
		return cls._instance
