from . import interfaces
import tuned.logs
import pickle
import os
import tuned.consts as consts

log = tuned.logs.get()

class PickleProvider(interfaces.Provider):
	__slots__ = ["_path", "_data"]

	def __init__(self, path=None):
		if path is None:
			path = consts.DEFAULT_STORAGE_FILE
		self._path = path
		self._data = {}

	def set(self, namespace, option, value):
		self._data.setdefault(namespace, {})
		self._data[namespace][option] = value

	def get(self, namespace, option, default=None):
		self._data.setdefault(namespace, {})
		return self._data[namespace].get(option, default)

	def unset(self, namespace, option):
		self._data.setdefault(namespace, {})
		if option in self._data[namespace]:
			del self._data[namespace][option]

	def save(self):
		try:
			log.debug("Saving %s" % str(self._data))
			with open(self._path, "w") as f:
				pickle.dump(self._data, f)
		except (OSError, IOError) as e:
			log.error("Error saving storage file '%s': %s" % (self._path, e))

	def load(self):
		try:
			with open(self._path, "r") as f:
				self._data = pickle.load(f)
		except (OSError, IOError) as e:
			log.debug("Error loading storage file '%s': %s" % (self._path, e))
			self._data = {}
		except EOFError:
			self._data = {}

	def clear(self):
		self._data.clear()
		try:
			os.unlink(self._path)
		except (OSError, IOError) as e:
			log.debug("Error removing storage file '%s': %s" % (self._path, e))
