class Storage(object):
	__slots__ = ["_storage_provider", "_namespace"]

	def __init__(self, storage_provider, namespace):
		self._storage_provider = storage_provider
		self._namespace = namespace

	def set(self, option, value):
		self._storage_provider.set(self._namespace, option, value)

	def get(self, option, default=None):
		return self._storage_provider.get(self._namespace, option, default)

	def unset(self, option):
		self._storage_provider.unset(self._namespace, option)
