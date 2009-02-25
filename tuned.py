import time,os,locale,ConfigParser

class Tuned:
	def __init__(self):
		self.interval = 10
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

	def init(self, path, cfgfile):
		self.config = ConfigParser.ConfigParser()
		self.config.read(cfgfile)
		if self.config.has_option("main", "interval"):
			self.interval = self.config.getint("main", "interval")
		else:
			self.config.set("main", "interval", self.interval)
		self.__initplugins__(path, "monitorplugins", self.mp)
		self.__initplugins__(path, "tuningplugins", self.tp)
		for p in self.mp:
			p.init(self.config)
		for p in self.tp:
			p.init(self.config)

	def run(self):
		print("Running...")
		while True:
			lh = {}
			for p in self.mp:
				lh.update(p.getLoad())
			for p in self.tp:
				p.setTuning(lh)
			time.sleep(self.interval)

	def cleanup(self, signum=0, frame=None):
		print("Cleanup...")
		for p in self.mp:
			p.cleanup()
		for p in self.tp:
			p.cleanup()

tuned = Tuned()
