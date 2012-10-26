import tuned.units.unit

class Factory(object):
	def create(self, name, type, plugin):
		return tuned.units.unit.Unit(name, type, plugin)
