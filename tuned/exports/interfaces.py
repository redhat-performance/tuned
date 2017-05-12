class ExportableInterface(object):
	pass

class ExporterInterface(object):
	def export(self, method, in_signature, out_signature):
		# to be overridden by concrete implementation
		raise NotImplementedError()

	def signal(self, method, out_signature):
		# to be overridden by concrete implementation
		raise NotImplementedError()

	def send_signal(self, signal, *args, **kwargs):
		# to be overridden by concrete implementation
		raise NotImplementedError()

	def start(self):
		raise NotImplementedError()

	def stop(self):
		raise NotImplementedError()
