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
import tuned.patterns

class ExportsController(tuned.patterns.Singleton):
	"""
	Controls and manages object interface exporting.
	"""

	def __init__(self):
		super(self.__class__, self).__init__()
		self._exporters = []
		self._objects = []
		self._exports_initialized = False

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

	def _initialize_exports(self):
		if self._exports_initialized:
			return

		for instance in self._objects:
			exportable = inspect.getmembers(instance, self._is_exportable_method)
			for name, method in exportable:
				self._export_method(method)

		self._exports_initialized = True

	def start(self):
		"""Start the exports."""
		self._initialize_exports()
		for exporter in self._exporters:
			exporter.start()

	def stop(self):
		"""Stop the exports."""
		for exporter in self._exporters:
			exporter.stop()
