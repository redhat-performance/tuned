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

import interfaces
import inspect

class ExportsController(object):
	"""
	Controls and manages object interface exporting.

	(Singleton class.)
	"""

	_instance = None

	def __init__(self):
		self._exporters = []
		self._objects = []

	@classmethod
	def get_instance(cls):
		"""Get class instance."""
		if cls._instance is None:
			cls._instance = cls()
		return cls._instance

	def register_exporter(self, instance):
		"""Register objects exporter."""
		self._exporters.append(instance)

	def register_object(self, instance):
		"""Register object to be exported."""
		self._objects.append(instance)

	def _is_exportable_method(self, method):
		"""Check if method was marked with @exports.export wrapper."""
		return inspect.ismethod(method) and hasattr(method, "export_params")

	def _export_method(self, method):
		"""Register method to all exporters."""
		for exporter in self._exporters:
			args = method.export_params[0]
			kwargs = method.export_params[1]
			exporter.export(method, *args, **kwargs)

	def run(self):
		"""Start the exports. This call is blocking at the moment."""
		# TODO: possibility to choose blocking/nonblocking

		for instance in self._objects:
			exportable = inspect.getmembers(instance, self._is_exportable_method)
			for name, method in exportable:
				self._export_method(method)

		# TODO: naive - handle concurrency between multiple exporters
		for exporter in self._exporters:
			exporter.run()
