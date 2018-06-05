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
from tuned.utils.commands import commands

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

debug = False

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
			response = self.tuned_daemon_exception_dialog.run()
			if response == 0:

#				 button Turn ON pressed
#				 switch_tuned_start_stop notify the switch which call funcion start_tuned

				self._start_tuned()
				self.tuned_daemon_exception_dialog.hide()
				return True
			elif response == 1:
				self.error_dialog('Tuned is shutting down.',
								  'Reason: missing communication with Tuned daemon.'
								  )
				return False
		return True

	def __init__(self):

		self.active_profile = None

		self._cmd = commands(debug)

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

		self.messagedialog_operation_error = \
			self.builder.get_object('messagedialogOperationError')
		self.tuned_daemon_exception_dialog = \
			self.builder.get_object('tunedDaemonExceptionDialog')
		self.dialog_add_plugin = \
			self.builder.get_object('dialogAddPlugin')
		self.tuned_daemon_exception_dialog.connect('destroy', lambda d: \
				self.tuned_daemon_exception_dialog.hide())
		self.cancel_button = self.builder.get_object('cancel_button')
		self.cancel_button.connect('clicked', lambda d: \
								   self.tuned_daemon_exception_dialog.hide())

		if not self._starting():
			return

		self.manager = \
			tuned.gtk.gui_profile_loader.GuiProfileLoader(tuned.consts.LOAD_DIRECTORIES)
		self.manager = \
			tuned.gtk.gui_profile_loader.GuiProfileLoader(tuned.consts.LOAD_DIRECTORIES)
		self.plugin_loader = \
			tuned.gtk.gui_plugin_loader.GuiPluginLoader()

		action_group = Gtk.ActionGroup('my_actions')
		self.builder.connect_signals(self)

		self.builder.connect_signals(self)

		#
		#	WINDOW MAIN
		#

		self.main_window = self.builder.get_object('mainWindow')

		#
		#	WINDOW PROFILE EDITOR
		#

		self.window_profile_editor = \
			self.builder.get_object('windowProfileEditor')
		self.window_profile_editor.connect('delete-event',
				self.on_delete_event)
		self.entry_profile_name = \
			self.builder.get_object('entryProfileName')
		self.combobox_include_profile = \
			self.builder.get_object('comboboxIncludeProfile')
		self.togglebutton_include_profile = \
			self.builder.get_object('togglebuttonIncludeProfile')
		self.notebook_plugins = \
			self.builder.get_object('notebookPlugins')

		self.button_add_plugin = \
			self.builder.get_object('buttonAddPlugin')
		self.button_remove_plugin = \
			self.builder.get_object('buttonRemovePlugin')
		self.button_open_raw = self.builder.get_object('buttonOpenRaw')
		self.button_cancel = self.builder.get_object('buttonCancel')

		self.button_open_raw.connect('clicked',
				self.execute_open_raw_button)
		self.button_add_plugin.connect('clicked',
				self.execute_add_plugin_to_notebook)
		self.button_remove_plugin.connect('clicked',
				self.execute_remove_plugin_from_notebook)
		self.button_cancel.connect('clicked',
								   self.execute_cancel_window_profile_editor)

		#
		#	WINDOW PROFILE EDITOR RAW
		#

		self.window_profile_editor_raw = \
			self.builder.get_object('windowProfileEditorRaw')
		self.window_profile_editor_raw.connect('delete-event',
				self.on_delete_event)
		self.button_apply = self.builder.get_object('buttonApply')
		self.button_apply.connect('clicked',
								  self.execute_apply_window_profile_editor_raw)
		self.button_cancel_raw = \
			self.builder.get_object('buttonCancelRaw')
		self.button_cancel_raw.connect('clicked',
				self.execute_cancel_window_profile_editor_raw)
		self.textview_profile_config_raw = \
			self.builder.get_object('textviewProfileConfigRaw')
		self.textview_profile_config_raw.set_editable(True)

		self.textview_plugin_avaible_text = \
			self.builder.get_object('textviewPluginAvaibleText')
		self.textview_plugin_documentation_text = \
			self.builder.get_object('textviewPluginDocumentationText')
		self.textview_plugin_avaible_text.set_editable(False)
		self.textview_plugin_documentation_text.set_editable(False)

		#
		#	DIALOG ABOUT
		#

		self.about_dialog = Gtk.AboutDialog.new()
		self.about_dialog.set_name(NAME)
		self.about_dialog.set_version(VERSION)
		self.about_dialog.set_license(LICENSE)
		self.about_dialog.set_wrap_license(True)
		self.about_dialog.set_copyright(COPYRIGHT)
		self.about_dialog.set_authors(AUTHORS)

		#
		#	GET WIDGETS
		#

		self.imagemenuitem_quit = \
			self.builder.get_object('imagemenuitemQuit')
		self.imagemenuitem_about = \
			self.builder.get_object('imagemenuitemAbout')

		self.label_actual_profile = \
			self.builder.get_object('labelActualProfile')
		self.label_recommended_profile = \
			self.builder.get_object('label_recommemnded_profile')
		self.label_dbus_status = \
			self.builder.get_object('labelDbusStatus')
		self.label_summary_profile = \
			self.builder.get_object('summaryProfileName')
		self.label_summary_included_profile = \
			self.builder.get_object('summaryIncludedProfileName')

		self.comboboxtext_fast_change_profile = \
			self.builder.get_object('comboboxtextFastChangeProfile')
		self.button_fast_change_profile = \
			self.builder.get_object('buttonFastChangeProfile')
		self.spinner_fast_change_profile = \
			self.builder.get_object('spinnerFastChangeProfile')
		self.spinner_fast_change_profile.hide()

		self.switch_tuned_start_stop = \
			self.builder.get_object('switchTunedStartStop')
		self.switch_tuned_startup_start_stop = \
			self.builder.get_object('switchTunedStartupStartStop')
		self.switch_tuned_admin_functions = \
			self.builder.get_object('switchTunedAdminFunctions')

		self.treeview_profile_manager = \
			self.builder.get_object('treeviewProfileManager')
		self.treeview_actual_plugins = \
			self.builder.get_object('treeviewActualPlugins')

		#
		#	SET WIDGETS
		#

		self.treestore_profiles = Gtk.ListStore(GObject.TYPE_STRING,
				GObject.TYPE_STRING)
		self.treestore_plugins = Gtk.ListStore(GObject.TYPE_STRING)
		for plugin in sorted(self.plugin_loader.plugins):
			self.treestore_plugins.append([plugin.name])
		self.combobox_plugins = \
			self.builder.get_object('comboboxPlugins')
		self.combobox_plugins.set_model(self.treestore_plugins)

		self.combobox_main_plugins = \
			self.builder.get_object('comboboxMainPlugins')
		self.combobox_main_plugins.set_model(self.treestore_plugins)
		self.combobox_main_plugins.connect('changed',
				self.on_changed_combobox_plugins)

		self.combobox_include_profile.set_model(self.treestore_profiles)
		cell = Gtk.CellRendererText()
		self.combobox_include_profile.pack_start(cell, True)
		self.combobox_include_profile.add_attribute(cell, 'text', 0)

		self.treeview_profile_manager.append_column(Gtk.TreeViewColumn('Type'
				, Gtk.CellRendererText(), text=1))
		self.treeview_profile_manager.append_column(Gtk.TreeViewColumn('Name'
				, Gtk.CellRendererText(), text=0))
		self.treeview_profile_manager.set_model(self.treestore_profiles)

		for profile_name in self.manager.get_names():
			if self.manager.is_profile_factory(profile_name):
				self.treestore_profiles.append([profile_name,
						consts.PREFIX_PROFILE_FACTORY])
			else:
				self.treestore_profiles.append([profile_name,
						consts.PREFIX_PROFILE_USER])
		self.treeview_profile_manager.get_selection().select_path(0)

		self.button_create_profile = \
			self.builder.get_object('buttonCreateProfile')
		self.button_upadte_selected_profile = \
			self.builder.get_object('buttonUpadteSelectedProfile')
		self.button_delete_selected_profile = \
			self.builder.get_object('buttonDeleteSelectedProfile')

		self.label_actual_profile.set_text(self.controller.active_profile())
		if self.config.get(consts.CFG_RECOMMEND_COMMAND):
			self.label_recommended_profile.set_text(self.controller.recommend_profile())
		self.listbox_summary_of_active_profile = \
			self.builder.get_object('listboxSummaryOfActiveProfile')

		self.data_for_listbox_summary_of_active_profile()
		self.comboboxtext_fast_change_profile.set_model(self.treestore_profiles)
		self.label_dbus_status.set_text(str(bool(self.controller.is_running())))

		self.switch_tuned_start_stop.set_active(True)
		self.switch_tuned_startup_start_stop.set_active(self.service_run_on_start_up('tuned'
				))
		self.switch_tuned_admin_functions.set_active(self.is_admin)

		self.menu_add_plugin_value = \
			self.builder.get_object('menuAddPluginValue')

		self.add_plugin_value_action = \
			self.builder.get_object('addPluginValue')
		self.add_custom_plugin_value = \
			self.builder.get_object('addCustomPluginValue')
		self.delete_plugin_value_action = \
			self.builder.get_object('deletePluginValue')
		self.add_plugin_value_action.connect('activate',
				self.add_plugin_value_to_treeview)
		self.add_custom_plugin_value.connect('activate',
				self.add_custom_plugin_value_to_treeview)
		self.delete_plugin_value_action.connect('activate',
				self.delete_plugin_value_to_treeview)

		#
		#	CONNECTIONS
		#

		self.imagemenuitem_quit.connect('activate', Gtk.main_quit)
		self.imagemenuitem_about.connect('activate', self.execute_about)

		self.comboboxtext_fast_change_profile.set_active(self.get_iter_from_model_by_name(self.comboboxtext_fast_change_profile.get_model(),
				self.controller.active_profile()))
		self.button_fast_change_profile.connect('clicked',
				self.execute_change_profile)

		self.switch_tuned_start_stop.connect('notify::active',
				self.execute_switch_tuned)
		self.switch_tuned_startup_start_stop.connect('notify::active',
				self.execute_switch_tuned)
		self.switch_tuned_admin_functions.connect('notify::active',
				self.execute_switch_tuned_admin_functions)

		self.button_create_profile.connect('clicked',
				self.execute_create_profile)
		self.button_upadte_selected_profile.connect('clicked',
				self.execute_update_profile)
		self.button_delete_selected_profile.connect('clicked',
				self.execute_remove_profile)

		self.button_confirm_profile_create = \
			self.builder.get_object('buttonConfirmProfileCreate')
		self.button_confirm_profile_update = \
			self.builder.get_object('buttonConfirmProfileUpdate')

		self.button_confirm_profile_create.connect('clicked',
				self.on_click_button_confirm_profile_create)
		self.button_confirm_profile_update.connect('clicked',
				self.on_click_button_confirm_profile_update)
		self.editing_profile_name = None
		self.treeview_actual_plugins.connect('row-activated',
				self.on_treeview_click)

#		 self.treeview_profile_manager.connect('row-activated',lambda x,y,z: self.execute_update_profile(x,y))
#  TO DO: need to be fixed! - double click on treeview

		self.main_window.connect('destroy', Gtk.main_quit)
		self.main_window.show()
		Gtk.main()

	def get_iter_from_model_by_name(self, model, item_name):
		'''
		Return iter from model selected by name of item in this model
		'''

		model = self.combobox_include_profile.get_model()
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
			response = self.tuned_daemon_exception_dialog.run()
			if response == 0:

#				 button Turn ON pressed
#				 switch_tuned_start_stop notify the switch which call funcion start_tuned

				try:
					self._start_tuned()
					self.tuned_daemon_exception_dialog.hide()
					self.switch_tuned_start_stop.set_active(True)
					return True
				except:
					self.tuned_daemon_exception_dialog.hide()
					return False
			else:
				self.tuned_daemon_exception_dialog.hide()
				return False

	def data_for_listbox_summary_of_active_profile(self):
		"""
		This add rows to object listbox_summary_of_active_profile.
		Row consist of grid. Inside grid on first possition is label, second possition is vertical grid.
		label = name of plugin
		verical grid consist of labels where are stored values for plugin option and value.

		This method is emited after change profile and on startup of app.
		"""

		for row in self.listbox_summary_of_active_profile:
			self.listbox_summary_of_active_profile.remove(row)

		if self.is_tuned_connection_ok():
			self.active_profile = \
				self.manager.get_profile(self.controller.active_profile())
		else:
			self.active_profile = None
		self.label_summary_profile.set_text(self.active_profile.name)
		try:
			self.label_summary_included_profile.set_text(self.active_profile.options['include'
					])
		except:

			# keyerror probably

			self.label_summary_included_profile.set_text('None')

		row = Gtk.ListBoxRow()
		box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
		plugin_name = Gtk.Label()
		plugin_name.set_markup('<b>Plugin Name</b>')
		plugin_option = Gtk.Label()
		plugin_option.set_markup('<b>Plugin Options</b>')
		box.pack_start(plugin_name, True, True, 0)
		box.pack_start(plugin_option, True, True, 0)
		row.add(box)

		self.listbox_summary_of_active_profile.add(row)

		sep = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
		self.listbox_summary_of_active_profile.add(sep)
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
			self.listbox_summary_of_active_profile.add(row)
			separator = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
			self.listbox_summary_of_active_profile.add(separator)
			separator.show()

		self.listbox_summary_of_active_profile.show_all()

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
		plugin = \
			self.plugin_loader.get_plugin(self.combobox_main_plugins.get_active_text())
		if plugin is None:
			self.textview_plugin_avaible_text.get_buffer().set_text('')
			self.textview_plugin_documentation_text.get_buffer().set_text(''
					)
			return
		options = '\n'.join('%s = %r' % (key, val) for (key, val) in
							plugin._get_config_options().items())

		self.textview_plugin_avaible_text.get_buffer().set_text(options)
		self.textview_plugin_documentation_text.get_buffer().set_text(plugin.__doc__)

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
			if self.window_profile_editor.is_active():
				self.error_dialog('You are ediding '
								  + self.editing_profile_name
								  + ' profile.',
								  'Please close edit window and try again.'
								  )
				return
			self.manager.remove_profile(profile, is_admin=self.is_admin)
			for item in self.treestore_profiles:
				if item[0] == profile:
					iter = self.treestore_profiles.get_iter(item.path)
					self.treestore_profiles.remove(iter)
		except ManagerException as ex:
			self.error_dialog('Profile can not be remove', ex.__str__())

	def execute_cancel_window_profile_editor(self, button):
		self.window_profile_editor.hide()

	def execute_cancel_window_profile_editor_raw(self, button):
		self.window_profile_editor_raw.hide()

	def execute_open_raw_button(self, button):
		profile_name = self.get_treeview_selected()
		text_buffer = self.textview_profile_config_raw.get_buffer()
		text_buffer.set_text(self.manager.get_raw_profile(profile_name))
		self.window_profile_editor_raw.show_all()

	def execute_add_plugin_to_notebook(self, button):
		if self.choose_plugin_dialog() == 1:
			plugin_name = self.combobox_plugins.get_active_text()
			plugin_to_tab = None
			for plugin in self.plugin_loader.plugins:
				if plugin.name == plugin_name:
					for children in self.notebook_plugins:
						if plugin_name \
							== self.notebook_plugins.get_menu_label_text(children):
							self.error_dialog('Plugin ' + plugin_name
									+ ' is already in profile.', '')
							return
					plugin_to_tab = plugin
					self.notebook_plugins.append_page_menu(self.treeview_for_data(plugin_to_tab._get_config_options()),
							Gtk.Label(plugin_to_tab.name),
							Gtk.Label(plugin_to_tab.name))

					self.notebook_plugins.show_all()

	def execute_remove_plugin_from_notebook(self, data):
		treestore = Gtk.ListStore(GObject.TYPE_STRING)
		for children in self.notebook_plugins.get_children():
			treestore.append([self.notebook_plugins.get_menu_label_text(children)])
		self.combobox_plugins.set_model(treestore)

		response_of_dialog = self.choose_plugin_dialog()

		if response_of_dialog == 1:

#			 ok button pressed

			selected = self.combobox_plugins.get_active_text()
			for children in self.notebook_plugins.get_children():
				if self.notebook_plugins.get_menu_label_text(children) \
					== selected:
					self.notebook_plugins.remove(children)
			self.combobox_plugins.set_model(self.treestore_plugins)

	def execute_apply_window_profile_editor_raw(self, data):
		text_buffer = self.textview_profile_config_raw.get_buffer()
		start = text_buffer.get_start_iter()
		end = text_buffer.get_end_iter()
		profile_name = self.get_treeview_selected()
		self.manager.set_raw_profile(profile_name,
				text_buffer.get_text(start, end, True))
		self.error_dialog('Profile Editor will be closed.',
						  'for next updates reopen profile.')
		self.window_profile_editor.hide()
		self.window_profile_editor_raw.hide()

#		 refresh window_profile_editor

	def execute_create_profile(self, button):
		self.reset_values_window_edit_profile()
		self.button_confirm_profile_create.show()
		self.button_confirm_profile_update.hide()
		self.button_open_raw.hide()

		for child in self.notebook_plugins.get_children():
			self.notebook_plugins.remove(child)
		self.window_profile_editor.show()

	def reset_values_window_edit_profile(self):
		self.entry_profile_name.set_text('')
		self.combobox_include_profile.set_active(0)
		for child in self.notebook_plugins.get_children():
			self.notebook_plugins.remove(child)

	def get_treeview_selected(self):
		"""
		Return value of treeview which is selected at calling moment of this function.
		"""

		selection = self.treeview_profile_manager.get_selection()
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

		self.manager.update_profile(profile_name, prof, self.is_admin)
		if self.manager.is_profile_factory(prof.name):
			prefix = consts.PREFIX_PROFILE_FACTORY
		else:
			prefix = consts.PREFIX_PROFILE_USER
		self.treestore_profiles.append([prof.name, prefix])
		self.window_profile_editor.hide()

	def data_to_profile_config(self):
		name = self.entry_profile_name.get_text()
		config = configobj.ConfigObj(list_values = False,
				interpolation = False)

		activated = self.combobox_include_profile.get_active()
		model = self.combobox_include_profile.get_model()

		include = model[activated][0]
		if self.togglebutton_include_profile.get_active():
			config['main'] = {'include': include}
		for children in self.notebook_plugins:
			acumulate_options = {}
			for item in children.get_model():
				if item[0] != 'None':
					acumulate_options[item[1]] = item[0]
			config[self.notebook_plugins.get_menu_label_text(children)] = \
				acumulate_options
		return profile.Profile(name, config)

	def on_click_button_confirm_profile_create(self, data):

		# try:

		prof = self.data_to_profile_config()
		self.manager.save_profile(prof)
		self.manager._load_all_profiles()
		self.treestore_profiles.append([prof.name, consts.PREFIX_PROFILE_USER])
		self.window_profile_editor.hide()

		# except ManagerException:
		#	 self.error_dialog("Profile with name " + prof.name
		#					   + " already exist.", "Please choose another name for profile")

	def execute_update_profile(self, data):

#		 if (self.treeview_profile_manager.get_activate_on_single_click()):
#			 print "returning"
#			 print self.treeview_profile_manager.get_activate_on_single_click()
#			 return

		self.button_confirm_profile_create.hide()
		self.button_confirm_profile_update.show()
		self.button_open_raw.show()
		label_update_profile = \
			self.builder.get_object('labelUpdateProfile')
		label_update_profile.set_text('Update Profile')

		for child in self.notebook_plugins.get_children():
			self.notebook_plugins.remove(child)

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
		if self.manager.is_profile_removable(self.editing_profile_name) \
			or self.is_admin:
			profile = \
				self.manager.get_profile(self.editing_profile_name)
			self.entry_profile_name.set_text(profile.name)
			model = self.combobox_include_profile.get_model()
			selected = 0
			self.togglebutton_include_profile.set_active(False)
			for item in model:
				try:
					if item[0] == profile.options['include']:
						selected = int(item.path.to_string())
						self.togglebutton_include_profile.set_active(True)
				except KeyError:
					pass

			#		 profile dont have include section

			self.combobox_include_profile.set_active(selected)

			# load all values not just normal

			for (name, unit) in list(profile.units.items()):
				self.notebook_plugins.append_page_menu(self.treeview_for_data(unit.options),
						Gtk.Label(unit.name), Gtk.Label(unit.name))
			self.notebook_plugins.show_all()
			self.window_profile_editor.show()
		else:
			self.error_dialog('You can not update Factory profile', '')

	def treeview_for_data(self, data):
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
		return treeview

	def execute_change_profile(self, button):
		"""
		Change profile in main window.
		"""

		self.spinner_fast_change_profile.show()
		self.spinner_fast_change_profile.start()
		if button is not None:
			text = \
				self.comboboxtext_fast_change_profile.get_active_text()
			if text is not None:
				if self.is_tuned_connection_ok():
					self.controller.switch_profile(text)
					self.label_actual_profile.set_text(self.controller.active_profile())
					self.data_for_listbox_summary_of_active_profile()
					self.active_profile = \
						self.manager.get_profile(self.controller.active_profile())
				else:
					self.label_actual_profile.set_text('')
			else:
				self.error_dialog('No profile selected', '')
		self.spinner_fast_change_profile.stop()
		self.spinner_fast_change_profile.hide()

	def execute_switch_tuned(self, switch, data):
		"""
		Suported switch_tuned_start_stop and switch_tuned_startup_start_stop.
		"""

		if switch == self.switch_tuned_start_stop:

#			 starts or stop tuned daemon

			if self.switch_tuned_start_stop.get_active():
				self.is_tuned_connection_ok()
			else:
				self._cmd.execute(['service', 'tuned', 'stop'])
				self.error_dialog('Tuned Daemon is turned off',
								  'Support of tuned is not running.')
		elif switch == self.switch_tuned_startup_start_stop:

#			 switch option for start tuned on start up

			if self.switch_tuned_startup_start_stop.get_active():
				self._cmd.execute(['systemctl', 'enable', 'tuned'])
			else:
				self._cmd.execute(['systemctl', 'disable', 'tuned'])
		else:
			raise NotImplementedError()

	def execute_switch_tuned_admin_functions(self, switch, data):
		self.is_admin = self.switch_tuned_admin_functions.get_active()

	def service_run_on_start_up(self, service):
		"""
		Depends on if tuned is set to run on startup of system return true if yes, else return false
		"""

		(temp, out) = self._cmd.execute(['systemctl', 'is-enabled', service])
		if temp == 0:
			return True
		return False

	def error_dialog(self, error, info):
		"""
		General error dialog with two fields. Primary and secondary text fields.
		"""

		self.messagedialog_operation_error.set_markup(error)
		self.messagedialog_operation_error.format_secondary_text(info)
		self.messagedialog_operation_error.run()
		self.messagedialog_operation_error.hide()

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

		self.combobox_plugins.set_active(0)
		self.button_add_plugin = \
			self.builder.get_object('buttonAddPluginDialog')
		self.button_cancel_add_plugin_dialog = \
			self.builder.get_object('buttonCloseAddPlugin')
		self.button_cancel_add_plugin_dialog.connect('clicked',
				lambda d: self.dialog_add_plugin.hide())
		self.dialog_add_plugin.connect('destroy', lambda d: \
				self.dialog_add_plugin.hide())
		response = self.dialog_add_plugin.run()
		self.dialog_add_plugin.hide()
		return response

	def on_treeview_click(self, treeview, event):

		if event.button == 3:
			popup = Gtk.Menu()
			popup.append(Gtk.MenuItem('add'))
			popup.append(Gtk.MenuItem('delete'))
			time = event.time
			self.menu_add_plugin_value.popup(
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

	def add_plugin_value_to_treeview(self, action):
		current_plugin = \
			self.notebook_plugins.get_tab_label(self.notebook_plugins.get_nth_page(self.notebook_plugins.get_current_page())).get_text()
		current_plugin_options = \
			self.plugin_loader.get_plugin(current_plugin)._get_config_options()
		curent_plugin_values_model = \
			self.notebook_plugins.get_nth_page(self.notebook_plugins.get_current_page()).get_model()

		treestore_plugins_values = Gtk.ListStore(GObject.TYPE_STRING)

		for vl_name in current_plugin_options:
			if not self.liststore_contains_item(curent_plugin_values_model,
					vl_name):
				treestore_plugins_values.append([vl_name])

		dialog_add_plugin_value = \
			self.builder.get_object('dialogAddPluginValue')
		dialog_add_plugin_value.connect('destroy', lambda d: \
				dialog_add_plugin_value.hide())
		combobox = self.builder.get_object('comboboxPluginsValues')
		combobox.set_model(treestore_plugins_values)

		response = dialog_add_plugin_value.run()
		dialog_add_plugin_value.hide()

		if response == 1:
			active = combobox.get_active_text()
			curent_plugin_values_model.append([current_plugin_options.get(active),
					active])
			return True
		return False

	def add_custom_plugin_value_to_treeview(self, action):
		curent_plugin_values_model = \
			self.notebook_plugins.get_nth_page(self.notebook_plugins.get_current_page()).get_model()

		dialog_add_custom_plugin_value = \
			self.builder.get_object('dialogAddCustomPluginValue')
		text = self.builder.get_object('entry2')
		dialog_add_custom_plugin_value.connect('destroy', lambda d: \
				dialog_add_custom_plugin_value.hide())

		response = dialog_add_custom_plugin_value.run()
		dialog_add_custom_plugin_value.hide()

		if response == 1:
			curent_plugin_values_model.append(['', text.get_text()])
			return True
		return False

	def delete_plugin_value_to_treeview(self, action):
		curent_plugin_values_tree = \
			self.notebook_plugins.get_nth_page(self.notebook_plugins.get_current_page())

		(model, iter) = \
			curent_plugin_values_tree.get_selection().get_selected()
		if model is None or iter is None:
			return False
		model.remove(iter)
		return True

	def _start_tuned(self):
		self._cmd.execute(['service', 'tuned', 'start'])
		time.sleep(10)
		self.controller = tuned.admin.DBusController(consts.DBUS_BUS,
				consts.DBUS_INTERFACE, consts.DBUS_OBJECT)


if __name__ == '__main__':

	if os.geteuid() != 0:
		try:
			# Explicitly disabling shell to be safe
			ec = subprocess.call(['pkexec', EXECNAME] + sys.argv[1:], shell = False)
		except (subprocess.CalledProcessError) as e:
			print('Error elevating privileges: %s' % e, file=sys.stderr)
		else:
			# If not pkexec error
			if ec not in [126, 127]:
				sys.exit(0)
		# In case of error elevating privileges
		print('Superuser permissions are required to run the daemon.', file=sys.stderr)
		sys.exit(1)
	base = Base()
