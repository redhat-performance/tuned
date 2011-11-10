#
# Author: Jan Vcelak <jvcelak@redhat.com>
#

class IExportable(object):
	pass

class IExporter(object):
	def export(self, method, in_signature, out_signature):
		# to be overriden by concrete implementation
		raise NotImplemented()

	def serve(self):
		raise NotImplemented()
