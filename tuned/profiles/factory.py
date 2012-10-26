import tuned.profiles.profile

class Factory(object):
	def create(self, name, config):
		return tuned.profiles.profile.Profile(name, config)
