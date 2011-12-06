# Copyright (C) 2008-2011 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
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
	if not isinstance(instance, interfaces.ExporterInterface):
		raise Exception()
	ctl = controller.ExportsController.get_instance()
	return ctl.register_exporter(instance)

def register_object(instance):
	if not isinstance(instance, interfaces.ExportableInterface):
		raise Exception()
	ctl = controller.ExportsController.get_instance()
	return ctl.register_object(instance)

def start():
	ctl = controller.ExportsController.get_instance()
	return ctl.start()

def stop():
	ctl = controller.ExportsController.get_instance()
	return ctl.stop()
