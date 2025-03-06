import tuned.profiles.profile

class Factory(object):
	def create(self, name, config, variables):
		return tuned.profiles.profile.Profile(name, config, variables)
