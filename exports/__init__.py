#
# Author: Jan Vcelak <jvcelak@redhat.com>
#

import controller
import interfaces

def export(*args, **kwargs):
	"""Decorator, use to mark exportable methods."""
	def wrapper(method):
		method.export_params = [ args, kwargs ]
		return method
	return wrapper

def register_exporter(instance):
	if not isinstance(instance, interfaces.IExporter):
		raise Exception()
	ctl = controller.ExportsController.get_instance()
	return ctl.register_exporter(instance)

def register_object(instance):
	if not isinstance(instance, interfaces.IExportable):
		raise Exception()
	ctl = controller.ExportsController.get_instance()
	return ctl.register_object(instance)

def run():
	ctl = controller.ExportsController.get_instance()
	return ctl.run()
