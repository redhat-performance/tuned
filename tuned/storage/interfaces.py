class Factory(object):
	def create(self, namespace):
		raise NotImplementedError()

class Provider(object):
	def set(self, namespace, option, value):
		raise NotImplementedError()

	def get(self, namespace, option, default=None):
		raise NotImplementedError()

	def unset(self, namespace, option):
		raise NotImplementedError()

	def clear(self):
		raise NotImplementedError()

	def load(self):
		raise NotImplementedError()

	def save(self):
		raise NotImplementedError()
