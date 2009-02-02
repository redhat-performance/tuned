import time,os,locale

class Tuned:
	def __init__(self):
		self.mp = []
		self.tp = []

	def __initplugins__(self, path, module, store):
		_files = map(lambda v: v[:-3], filter(lambda v: v[-3:] == ".py" and \
                             v != "__init__.py" and \
                             v[0] != '.', \
                             os.listdir(path+"/"+module)))
		locale.setlocale(locale.LC_ALL, "C")
		_files.sort()
		locale.setlocale(locale.LC_ALL, "")
		for _i in _files:
			_cmd = "from %s.%s import _plugin" % (module, _i)
    			exec _cmd
			store.append(_plugin)

	def init(self, path):
		self.__initplugins__(path, "monitorplugins", self.mp)
		self.__initplugins__(path, "tuningplugins", self.tp)

	def run(self):
		print("Running...")
		while True:
			lh = {}
			for p in self.mp:
				lh.update(p.getLoad())
			for p in self.tp:
				p.setTuning(lh)
			time.sleep(10)

	def cleanup(self):
		print("Cleanup...")

tuned = Tuned()
