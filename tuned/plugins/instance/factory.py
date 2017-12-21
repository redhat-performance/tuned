from .instance import Instance

class Factory(object):
	def create(self, *args, **kwargs):
		instance = Instance(*args, **kwargs)
		return instance
