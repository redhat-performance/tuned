#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2014 Red Hat, Inc.
# Authors: Marek Staňa, Jaroslav Škarvada <jskarvad@redhat.com>
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

'''
Created on Oct 15, 2013

@author: mstana
'''
from __future__ import print_function
try:
    import gi
except ImportError:
    raise ImportError("Gtk3 backend requires pygobject to be installed.")

try:
    gi.require_version("Gtk", "3.0")
except AttributeError:
    raise ImportError(
        "pygobject version too old -- it must have require_version")
except ValueError:
    raise ImportError(
        "Gtk3 backend requires the GObject introspection bindings for Gtk 3 "
        "to be installed.")

try:
    from gi.repository import Gtk, GObject
except ImportError:
    raise ImportError("Gtk3 backend requires pygobject to be installed.")

import sys
import os
import time
import configobj
import subprocess

import tuned.logs
import tuned.consts as consts
import tuned.version as version
import tuned.admin.dbus_controller
import tuned.gtk.gui_profile_loader
import tuned.gtk.gui_plugin_loader
import tuned.profiles.profile as profile
import tuned.utils.global_config
from tuned.gtk.tuned_dialog import TunedDialog

from tuned.gtk.managerException import ManagerException

EXECNAME = '/usr/sbin/tuned-gui'
GLADEUI = '/usr/share/tuned/ui/tuned-gui.glade'
LICENSE = 'GNU GPL version 2 or later <http://gnu.org/licenses/gpl.html>'
NAME = 'tuned'
VERSION = 'tuned ' + str(version.TUNED_VERSION_MAJOR) + '.' + \
	str(version.TUNED_VERSION_MINOR) + '.' + str(version.TUNED_VERSION_PATCH)
COPYRIGHT = 'Copyright (C) 2014 Red Hat, Inc.'

AUTHORS = [
	'',
	'Marek Staňa',
	'Jaroslav Škarvada <jskarvad@redhat.com>',
	]

class Base(object):

	"""
	GUI class for program Tuned.
	"""

	is_admin = False

	def _starting(self):
		try:
			self.controller = \
				tuned.admin.DBusController(consts.DBUS_BUS,
					consts.DBUS_INTERFACE, consts.DBUS_OBJECT)
			self.controller.is_running()
		except tuned.admin.exceptions.TunedAdminDBusException as ex:
			response = self._gobj('tunedDaemonExceptionDialog').run()
			if response == 0:

#				 button Turn ON pressed
#				 switch_tuned_start_stop notify the switch which call funcion start_tuned

				self._start_tuned()
				self._gobj('tunedDaemonExceptionDialog').hide()
				return True
			else:
				self.error_dialog('Tuned is shutting down.',
								  'Reason: missing communication with Tuned daemon.'
								  )
				return False
		return True

	def __init__(self):

		self.active_profile = None

		self.config = tuned.utils.global_config.GlobalConfig()
		self.builder = Gtk.Builder()
		try:
			self.builder.add_from_file(GLADEUI)
		except GObject.GError as e:
			print("Error loading '%s'" % GLADEUI, file=sys.stderr)
			sys.exit(1)

		#
		#	DIALOGS
		#

		self.builder.connect_signals(self)

		if not self._starting():
			return

		self.manager = tuned.gtk.gui_profile_loader.GuiProfileLoader(
			tuned.consts.LOAD_DIRECTORIES)

		self.plugin_loader = tuned.gtk.gui_plugin_loader.GuiPluginLoader()

		self._build_about_dialog()

		#
		#	SET WIDGETS
		#

		self.treestore_profiles = Gtk.ListStore(GObject.TYPE_STRING,
				GObject.TYPE_STRING)
		self.treestore_plugins = Gtk.ListStore(GObject.TYPE_STRING)
		for plugin_name in self.plugin_loader.plugins:
			self.treestore_plugins.append([plugin_name])

		self._gobj('comboboxPlugins').set_model(self.treestore_plugins)

		self._gobj('comboboxMainPlugins').set_model(self.treestore_plugins)

		self._gobj('comboboxIncludeProfile').set_model(self.treestore_profiles)
		cell = Gtk.CellRendererText()
		self._gobj('comboboxIncludeProfile').pack_start(cell, True)
		self._gobj('comboboxIncludeProfile').add_attribute(cell, 'text', 0)

		self._gobj('treeviewProfileManager').append_column(Gtk.TreeViewColumn('Type'
				, Gtk.CellRendererText(), text=1))
		self._gobj('treeviewProfileManager').append_column(Gtk.TreeViewColumn('Name'
				, Gtk.CellRendererText(), text=0))
		self._gobj('treeviewProfileManager').set_model(self.treestore_profiles)

		self._update_profile_list()

		self._gobj('treeviewProfileManager').get_selection().select_path(0)

		self._gobj('labelActualProfile').set_text(self.controller.active_profile())
		if self.config.get(consts.CFG_RECOMMEND_COMMAND):
			self._gobj('label_recommemnded_profile').set_text(self.controller.recommend_profile())

		self.data_for_listbox_summary_of_active_profile()
		self._gobj('comboboxtextFastChangeProfile').set_model(self.treestore_profiles)
		self._gobj('labelDbusStatus').set_text(str(bool(self.controller.is_running())))

		self._gobj('switchTunedStartupStartStop').set_active(
			self.service_run_on_start_up('tuned'))

		self._gobj('switchTunedAdminFunctions').set_active(self.is_admin)

		self._gobj('comboboxtextFastChangeProfile').set_active(self.get_iter_from_model_by_name(self._gobj('comboboxtextFastChangeProfile').get_model(),
				self.controller.active_profile()))

		self.editing_profile_name = None

		# self.treeview_profile_manager.connect('row-activated',lambda x,y,z: self.execute_update_profile(x,y))
		# TO DO: need to be fixed! - double click on treeview

		self._gobj('mainWindow').show()
		Gtk.main()

	def get_iter_from_model_by_name(self, model, item_name):
		'''
		Return iter from model selected by name of item in this model
		'''

		model = self._gobj('comboboxIncludeProfile').get_model()
		selected = 0
		for item in model:
			try:
				if item[0] == item_name:
					selected = int(item.path.to_string())
			except KeyError:
				pass
		return selected

	def is_tuned_connection_ok(self):
		"""
		Result True, False depends on if tuned daemon is running. If its not runing this method try to start tuned.
		"""

		try:
			self.controller.is_running()
			return True
		except tuned.admin.exceptions.TunedAdminDBusException:
			response = self._gobj('tunedDaemonExceptionDialog').run()
			if response == 0:

#				 button Turn ON pressed
#				 switch_tuned_start_stop notify the switch which call funcion start_tuned

				try:
					self._start_tuned()
					self._gobj('tunedDaemonExceptionDialog').hide()
					self._gobj('switchTunedStartStop').set_active(True)
					return True
				except:
					self._gobj('tunedDaemonExceptionDialog').hide()
					return False
			else:
				self._gobj('tunedDaemonExceptionDialog').hide()
				return False

	def data_for_listbox_summary_of_active_profile(self):
		"""
		This add rows to object listbox_summary_of_active_profile.
		Row consist of grid. Inside grid on first possition is label, second possition is vertical grid.
		label = name of plugin
		verical grid consist of labels where are stored values for plugin option and value.

		This method is emited after change profile and on startup of app.
		"""

		for row in self._gobj('listboxSummaryOfActiveProfile'):
			self._gobj('listboxSummaryOfActiveProfile').remove(row)

		if self.is_tuned_connection_ok():
			self.active_profile = \
				self.manager.get_profile(self.controller.active_profile())
		else:
			self.active_profile = None
		self._gobj('summaryProfileName').set_text(self.active_profile.name)
		try:
			self._gobj('summaryIncludedProfileName').set_text(self.active_profile.options['include'
					])
		except:

			# keyerror probably

			self._gobj('summaryIncludedProfileName').set_text('None')

		row = Gtk.ListBoxRow()
		box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
		plugin_name = Gtk.Label()
		plugin_name.set_markup('<b>Plugin Name</b>')
		plugin_option = Gtk.Label()
		plugin_option.set_markup('<b>Plugin Options</b>')
		box.pack_start(plugin_name, True, True, 0)
		box.pack_start(plugin_option, True, True, 0)
		row.add(box)

		self._gobj('listboxSummaryOfActiveProfile').add(row)

		sep = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
		self._gobj('listboxSummaryOfActiveProfile').add(sep)
		sep.show()

		for u in self.active_profile.units:
			row = Gtk.ListBoxRow()
			hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
						   spacing=0)
			hbox.set_homogeneous(True)
			row.add(hbox)
			label = Gtk.Label()
			label.set_markup(u)
			label.set_justify(Gtk.Justification.LEFT)
			hbox.pack_start(label, False, True, 1)

			grid = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
						   spacing=0)
			grid.set_homogeneous(True)
			for o in self.active_profile.units[u].options:
				label_option = Gtk.Label()
				label_option.set_markup(o + ' = ' + '<b>'
						+ self.active_profile.units[u].options[o]
						+ '</b>')
				grid.pack_start(label_option, False, True, 0)

			hbox.pack_start(grid, False, True, 0)
			self._gobj('listboxSummaryOfActiveProfile').add(row)
			separator = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
			self._gobj('listboxSummaryOfActiveProfile').add(separator)
			separator.show()

		self._gobj('listboxSummaryOfActiveProfile').show_all()

	# def on_treeview_button_press_event(self, treeview, event):
	#	 popup = Gtk.Menu()
	#	 popup.append(Gtk.MenuItem('add'))
	#	 popup.append(Gtk.MenuItem('delete'))
	#
	#	 if event.button == 3:
	#		 x = int(event.x)
	#		 y = int(event.y)
	#		 time = event.time
	#		 pthinfo = treeview.get_path_at_pos(x, y)
	#		 if pthinfo is not None:
	#			 path, col, cellx, celly = pthinfo
	#			 treeview.grab_focus()
	#			 treeview.set_cursor(path, col, 0)
	#			 popup.popup(None, None, lambda menu, data:
	#			 (event.get_root_coords()[0], event.get_root_coords()[1], True), None, event.button, event.time)
	#		 return True

	def on_changed_combobox_plugins(self, combo):
		plugin_name = self._gobj('comboboxMainPlugins').get_active_text()
		plugin_parameters = self.plugin_loader.plugins.get(plugin_name, None)
		if plugin_parameters is None:
			self._gobj('textviewPluginAvaibleText').get_buffer().set_text('')
			self._gobj('textviewPluginDocumentationText').get_buffer().set_text(''
					)
			return
		plugin_hints = self.plugin_loader.get_plugin_hints(plugin_name)
		options = ''
		for (key, val) in plugin_parameters.items():
			options += '%s = %r\n' % (key, str(val))
			hint = plugin_hints.get(key, None)
			if hint:
				options += '%s\n' % (str(hint))

		self._gobj('textviewPluginAvaibleText').get_buffer().set_text(options)
		plugin_doc = self.plugin_loader.get_plugin_doc(plugin_name)
		self._gobj('textviewPluginDocumentationText').get_buffer().set_text(
			plugin_doc
		)

	def on_delete_event(self, window, data):
		window.hide()
		return True

	def _get_active_profile_name(self):
		return self.manager.get_profile(self.controller.active_profile()).name

	def execute_remove_profile(self, button):
		profile = self.get_treeview_selected()
		try:
			if self._get_active_profile_name() == profile:
				self.error_dialog('You can not remove active profile',
								  'Please deactivate profile by choosind another!'
								  )
				return
			if profile is None:
				self.error_dialog('No profile selected!', '')
				return
			if self._gobj('windowProfileEditor').is_active():
				self.error_dialog('You are ediding '
								  + self.editing_profile_name
								  + ' profile.',
								  'Please close edit window and try again.'
								  )
				return

			try:
				self.manager.remove_profile(profile, is_admin=self.is_admin)
			except ManagerException:
				self.error_dialog('failed to authorize', '')
				return

			for item in self.treestore_profiles:
				if item[0] == profile:
					iter = self.treestore_profiles.get_iter(item.path)
					self.treestore_profiles.remove(iter)
		except ManagerException as ex:
			self.error_dialog('Profile can not be remove', ex.__str__())

	def execute_cancel_window_profile_editor(self, button):
		self._gobj('windowProfileEditor').hide()

	def execute_cancel_window_profile_editor_raw(self, button):
		self._gobj('windowProfileEditorRaw').hide()

	def execute_open_raw_button(self, button):
		profile_name = self.get_treeview_selected()
		text_buffer = self._gobj('textviewProfileConfigRaw').get_buffer()
		text_buffer.set_text(self.manager.get_raw_profile(profile_name))
		self._gobj('windowProfileEditorRaw').show_all()

	def execute_add_plugin_to_notebook(self, button):
		if self.choose_plugin_dialog() == 1:
			plugin_name = self._gobj('comboboxPlugins').get_active_text()
			plugin_to_tab = None
			for plugin in self.plugin_loader.plugins:
				if plugin == plugin_name:
					for children in self._gobj('notebookPlugins'):
						if plugin_name \
							== self._gobj('notebookPlugins').get_menu_label_text(children):
							self.error_dialog('Plugin ' + plugin_name
									+ ' is already in profile.', '')
							return
					config_options = self.plugin_loader.plugins[plugin]
					self._gobj('notebookPlugins').append_page_menu(
							self.treeview_for_data(
								config_options, plugin),
							Gtk.Label(plugin),
							Gtk.Label(plugin)
							)

					self._gobj('notebookPlugins').show_all()

	def execute_remove_plugin_from_notebook(self, data):
		treestore = Gtk.ListStore(GObject.TYPE_STRING)
		for children in self._gobj('notebookPlugins').get_children():
			treestore.append([self._gobj('notebookPlugins').get_menu_label_text(children)])
		self._gobj('comboboxPlugins').set_model(treestore)

		response_of_dialog = self.choose_plugin_dialog()

		if response_of_dialog == 1:

#			 ok button pressed

			selected = self._gobj('comboboxPlugins').get_active_text()
			for children in self._gobj('notebookPlugins').get_children():
				if self._gobj('notebookPlugins').get_menu_label_text(children) \
					== selected:
					self._gobj('notebookPlugins').remove(children)
			self._gobj('comboboxPlugins').set_model(self.treestore_plugins)

	def execute_apply_window_profile_editor_raw(self, data):
		text_buffer = self._gobj('textviewProfileConfigRaw').get_buffer()
		start = text_buffer.get_start_iter()
		end = text_buffer.get_end_iter()
		profile_name = self.get_treeview_selected()
		try:
			self.manager.set_raw_profile(profile_name,
				text_buffer.get_text(start, end, True))
		except Exception:
			self.error_dialog('Error while parsing raw configuration')
			return

		self.error_dialog('Profile Editor will be closed.',
						  'for next updates reopen profile.')
		self._gobj('windowProfileEditor').hide()
		self._gobj('windowProfileEditorRaw').hide()

#		 refresh window_profile_editor

	def execute_create_profile(self, button):
		self.reset_values_window_edit_profile()
		self._gobj('buttonConfirmProfileCreate').show()
		self._gobj('buttonConfirmProfileUpdate').hide()
		self._gobj('buttonOpenRaw').hide()

		for child in self._gobj('notebookPlugins').get_children():
			self._gobj('notebookPlugins').remove(child)
		self._gobj('windowProfileEditor').show()

	def reset_values_window_edit_profile(self):
		self._gobj('entryProfileName').set_text('')
		self._gobj('comboboxIncludeProfile').set_active(0)
		for child in self._gobj('notebookPlugins').get_children():
			self._gobj('notebookPlugins').remove(child)

	def get_treeview_selected(self):
		"""
		Return value of treeview which is selected at calling moment of this function.
		"""

		selection = self._gobj('treeviewProfileManager').get_selection()
		(model, iter) = selection.get_selected()
		if iter is None:
			self.error_dialog('No profile selected', '')
		return self.treestore_profiles.get_value(iter, 0)

	def on_click_button_confirm_profile_update(self, data):
		profile_name = self.get_treeview_selected()
		prof = self.data_to_profile_config()
		for item in self.treestore_profiles:
			try:
				if item[0] == profile_name:
					iter = self.treestore_profiles.get_iter(item.path)
					self.treestore_profiles.remove(iter)
			except KeyError:
				raise KeyError('this cant happen')

		try:
			self.manager.update_profile(profile_name, prof, self.is_admin)
		except ManagerException:
			self.error_dialog('failed to authorize', '')
			return

		if self.manager.is_profile_factory(prof.name):
			prefix = consts.PREFIX_PROFILE_FACTORY
		else:
			prefix = consts.PREFIX_PROFILE_USER
		self.treestore_profiles.append([prof.name, prefix])
		self._gobj('windowProfileEditor').hide()

	def data_to_profile_config(self):
		name = self._gobj('entryProfileName').get_text()
		config = configobj.ConfigObj(list_values = False,
				interpolation = False)

		activated = self._gobj('comboboxIncludeProfile').get_active()
		model = self._gobj('comboboxIncludeProfile').get_model()

		include = model[activated][0]
		if self._gobj('togglebuttonIncludeProfile').get_active():
			config['main'] = {'include': include}
		for children in self._gobj('notebookPlugins'):
			acumulate_options = {}
			for item in children.get_model():
				if item[0] != 'None':
					acumulate_options[item[1]] = item[0]
			config[self._gobj('notebookPlugins').get_menu_label_text(children)] = \
				acumulate_options
		return profile.Profile(name, config)

	def on_click_button_confirm_profile_create(self, data):

		# try:

		prof = self.data_to_profile_config()
		try:
			self.manager.save_profile(prof)
		except ManagerException:
			self.error_dialog('failed to authorize', '')
			return
		self.manager._load_all_profiles()
		self.treestore_profiles.append([prof.name, consts.PREFIX_PROFILE_USER])
		self._gobj('windowProfileEditor').hide()

		# except ManagerException:
		#	 self.error_dialog("Profile with name " + prof.name
		#					   + " already exist.", "Please choose another name for profile")

	def execute_update_profile(self, data):

#		 if (self.treeview_profile_manager.get_activate_on_single_click()):
#			 print "returning"
#			 print self.treeview_profile_manager.get_activate_on_single_click()
#			 return

		self._gobj('buttonConfirmProfileCreate').hide()
		self._gobj('buttonConfirmProfileUpdate').show()
		self._gobj('buttonOpenRaw').show()
		label_update_profile = \
			self.builder.get_object('labelUpdateProfile')
		label_update_profile.set_text('Update Profile')

		for child in self._gobj('notebookPlugins').get_children():
			self._gobj('notebookPlugins').remove(child)

		self.editing_profile_name = self.get_treeview_selected()

		if self.editing_profile_name is None:
			self.error_dialog('No profile Selected',
							  'To update profile please select profile.'
							  )
			return
		if self._get_active_profile_name() == self.editing_profile_name:
			self.error_dialog('You can not update active profile',
							  'Please deactivate profile by choosing another!'
							  )
			return

		copied_profile = None

		if not self.manager.is_profile_removable(self.editing_profile_name):
			if not self.manager.get_profile(
					self.editing_profile_name + '-modified'):
				if not TunedDialog('System profile can not be modified '
							+ 'but you can create its copy',
							'create copy',
							'cancel'
							).run():
					return

				copied_profile = self.manager.get_profile(
					self.editing_profile_name)
				copied_profile.name = self.editing_profile_name + '-modified'
				try:
					self.manager.save_profile(copied_profile)
				except ManagerException:
					self.error_dialog('failed to authorize', '')
					return
			else:
				if not TunedDialog('System profile can not be modified '
							+ 'but you can use its copy',
							'open copy',
							'cancel'
							).run():
					return
				copied_profile = self.manager.get_profile(
					self.editing_profile_name + '-modified')
			self._update_profile_list()
			for row in range(len(self.treestore_profiles)):
				if self.treestore_profiles[row][0] == self.editing_profile_name + '-modified':
					self._gobj('treeviewProfileManager').get_selection().select_path(row)
					break

		profile = copied_profile or self.manager.get_profile(self.editing_profile_name)
		self._gobj('entryProfileName').set_text(profile.name)
		model = self._gobj('comboboxIncludeProfile').get_model()
		selected = 0
		self._gobj('togglebuttonIncludeProfile').set_active(False)
		for item in model:
			try:
				if item[0] == profile.options['include']:
					selected = int(item.path.to_string())
					self._gobj('togglebuttonIncludeProfile').set_active(True)
			except KeyError:
				pass

		#		 profile dont have include section

		self._gobj('comboboxIncludeProfile').set_active(selected)

		# load all values not just normal

		for (name, unit) in list(profile.units.items()):
			self._gobj('notebookPlugins').append_page_menu(self.treeview_for_data(unit.options, unit.name),
					Gtk.Label(unit.name), Gtk.Label(unit.name))
		self._gobj('notebookPlugins').show_all()
		self._gobj('windowProfileEditor').show()

	def treeview_for_data(self, data, plugin_name):
		"""
		This prepare treestore and treeview for data and return treeview
		"""

		treestore = Gtk.ListStore(GObject.TYPE_STRING,
								  GObject.TYPE_STRING)

		for (option, value) in list(data.items()):
			treestore.append([str(value), option])
		treeview = Gtk.TreeView(treestore)
		renderer = Gtk.CellRendererText()
		column_option = Gtk.TreeViewColumn('Option', renderer, text=0)
		column_value = Gtk.TreeViewColumn('Value', renderer, text=1)
		treeview.append_column(column_value)
		treeview.append_column(column_option)
		treeview.enable_grid_lines = True
		treeview.connect('row-activated', self.change_value_dialog)
		treeview.connect('button_press_event', self.on_treeview_click)
		treeview.set_property('has-tooltip',True)
		model = treeview.get_model()
		treeview.connect(
			'query-tooltip',
			lambda widget, x, y, keyboard_mode, tooltip:
				self.on_option_tooltip(widget,
					x,
					y,
					keyboard_mode,
					tooltip,
					plugin_name,
					model
					)
			)
		return treeview

	def execute_change_profile(self, button):
		"""
		Change profile in main window.
		"""

		self._gobj('spinnerFastChangeProfile').show()
		self._gobj('spinnerFastChangeProfile').start()
		if button is not None:
			text = \
				self._gobj('comboboxtextFastChangeProfile').get_active_text()
			if text is not None:
				if self.is_tuned_connection_ok():
					self.controller.switch_profile(text)
					self._gobj('labelActualProfile').set_text(self.controller.active_profile())
					self.data_for_listbox_summary_of_active_profile()
					self.active_profile = \
						self.manager.get_profile(self.controller.active_profile())
				else:
					self._gobj('labelActualProfile').set_text('')
			else:
				self.error_dialog('No profile selected', '')
		self._gobj('spinnerFastChangeProfile').stop()
		self._gobj('spinnerFastChangeProfile').hide()

	def execute_switch_tuned(self, switch, data):
		"""
		Suported switch_tuned_start_stop and switch_tuned_startup_start_stop.
		"""

		if switch == self._gobj('switchTunedStartStop'):

#			 starts or stop tuned daemon

			if self._gobj('switchTunedStartStop').get_active():
				self.is_tuned_connection_ok()
			else:
				self._su_execute(['service', 'tuned', 'stop'])
				self.error_dialog('Tuned Daemon is turned off',
								  'Support of tuned is not running.')
		elif switch == self._gobj('switchTunedStartupStartStop'):

#			 switch option for start tuned on start up

			if self._gobj('switchTunedStartupStartStop').get_active():
				self._su_execute(['systemctl', 'enable', 'tuned'])
			else:
				self._su_execute(['systemctl', 'disable', 'tuned'])
		else:
			raise NotImplementedError()

	def execute_switch_tuned_admin_functions(self, switch, data):
		self.is_admin = self._gobj('switchTunedAdminFunctions').get_active()

	def service_run_on_start_up(self, service):
		"""
		Depends on if tuned is set to run on startup of system return true if yes, else return false
		"""

		temp = self._execute(['systemctl', 'is-enabled', service, '-q'])
		if temp == 0:
			return True
		return False

	def error_dialog(self, error, info):
		"""
		General error dialog with two fields. Primary and secondary text fields.
		"""

		self._gobj('messagedialogOperationError').set_markup(error)
		self._gobj('messagedialogOperationError').format_secondary_text(info)
		self._gobj('messagedialogOperationError').run()
		self._gobj('messagedialogOperationError').hide()

	def execute_about(self, widget):
		self.about_dialog.run()
		self.about_dialog.hide()

	def change_value_dialog(
		self,
		tree_view,
		path,
		treeview_column,
		):
		"""
		Shows up dialog after double click on treeview which has to be stored in notebook of plugins.
		Th``` dialog allows you to chagne specific option's value in plugin.
		"""

		model = tree_view.get_model()
		dialog = self.builder.get_object('changeValueDialog')
		button_apply = self.builder.get_object('buttonApplyChangeValue')
		button_cancel = self.builder.get_object('buttonCancel1')
		entry1 = self.builder.get_object('entry1')
		text = self.builder.get_object('labelTextDialogChangeValue')

		text.set_text(model.get_value(model.get_iter(path), 1))
		text = model.get_value(model.get_iter(path), 0)
		if text is not None:
			entry1.set_text(text)
		else:
			entry1.set_text('')
		dialog.connect('destroy', lambda d: dialog.hide())
		button_cancel.connect('clicked', lambda d: dialog.hide())

		if dialog.run() == 1:
			model.set_value(model.get_iter(path), 0, entry1.get_text())
		dialog.hide()

	def choose_plugin_dialog(self):
		"""
		Shows up dialog with combobox where are stored plugins available to add.
		"""

		self._gobj('comboboxPlugins').set_active(0)
		self.button_add_plugin_dialog = \
			self.builder.get_object('buttonAddPluginDialog')
		self.button_cancel_add_plugin_dialog = \
			self.builder.get_object('buttonCloseAddPlugin')
		self.button_cancel_add_plugin_dialog.connect('clicked',
				lambda d: self._gobj('dialogAddPlugin').hide())
		self._gobj('dialogAddPlugin').connect('destroy', lambda d: \
				self._gobj('dialogAddPlugin').hide())
		response = self._gobj('dialogAddPlugin').run()
		self._gobj('dialogAddPlugin').hide()
		return response

	def on_treeview_click(self, treeview, event):

		if event.button == 3:
			popup = Gtk.Menu()
			popup.append(Gtk.MenuItem('add'))
			popup.append(Gtk.MenuItem('delete'))
			time = event.time
			self._gobj('menuAddPluginValue').popup(
				None,
				None,
				None,
				None,
				event.button,
				time,
				)
			return True

	@staticmethod
	def liststore_contains_item(liststore, item):
		for liststore_item in liststore:
			if liststore_item[1] == item:
				return True
		return False

	def _start_tuned(self):
		self._su_execute(['service', 'tuned', 'start'])
		time.sleep(10)
		self.controller = tuned.admin.DBusController(consts.DBUS_BUS,
				consts.DBUS_INTERFACE, consts.DBUS_OBJECT)

	def _gobj(self, id):
		""" Wrapper for self.builder.get_object
		"""
		return self.builder.get_object(id)

	def HideTunedDaemonExceptionDialog(self, sender):
		self._gobj('tunedDaemonExceptionDialog').hide()

	def _build_about_dialog(self):
		self.about_dialog = Gtk.AboutDialog.new()
		self.about_dialog.set_name(NAME)
		self.about_dialog.set_version(VERSION)
		self.about_dialog.set_license(LICENSE)
		self.about_dialog.set_wrap_license(True)
		self.about_dialog.set_copyright(COPYRIGHT)
		self.about_dialog.set_authors(AUTHORS)

	def _update_profile_list(self):
		self.treestore_profiles.clear()

		for profile_name in self.manager.get_names():
			if self.manager.is_profile_factory(profile_name):
				self.treestore_profiles.append([profile_name,
						consts.PREFIX_PROFILE_FACTORY])
			else:
				self.treestore_profiles.append([profile_name,
						consts.PREFIX_PROFILE_USER])
		self._gobj('comboboxIncludeProfile').set_model(self.treestore_profiles)
		self._gobj('comboboxtextFastChangeProfile').set_model(
			self.treestore_profiles)
		self._gobj('treeviewProfileManager').set_model(self.treestore_profiles)
		self._gobj('comboboxtextFastChangeProfile').set_active(
			self.get_iter_from_model_by_name(
				self._gobj('comboboxtextFastChangeProfile').get_model(),
					self.controller.active_profile()))

	def _su_execute(self, args):
		args = ['pkexec'] + args
		rc = subprocess.call(args)
		return rc

	def _execute(self, args):
		rc = subprocess.call(args)
		return rc

	def on_option_tooltip(self, widget, x, y, keyboard_mode, tooltip, plugin_name, model):
		path = widget.get_path_at_pos(x, y)
		plugin_hints = self.plugin_loader.get_plugin_hints(plugin_name)
		if plugin_hints is None or len(plugin_hints) == 0:
			return False
		if not path:
			row_count = model.iter_n_children(None)
			if (row_count == 0):
				return False
			iterator = model.get_iter(row_count - 1)
			option_name = model.get_value(iterator, 1)
		elif int(str(path[0])) < 1:
			return False
		else:
			iterator = model.get_iter(int(str(path[0])) -1)
			option_name = model.get_value(iterator, 1)
		path = model.get_path(iterator)
		hint = plugin_hints.get(option_name, None)
		if not hint:
			return False
		tooltip.set_text(hint)
		widget.set_tooltip_row(tooltip, path)
		return True

	def gtk_main_quit(self, sender):
		Gtk.main_quit()


if __name__ == '__main__':

	base = Base()
