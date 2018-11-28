# -*- coding: utf-8 -*-

# Copyright (C) 2008-2014 Red Hat, Inc.
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
Created on Mar 30, 2014

@author: mstana
'''

import importlib
from validate import Validator

import tuned.consts as consts
import tuned.logs

import configobj as ConfigObj
from tuned.exceptions import TunedException

from tuned.admin.dbus_controller import DBusController

__all__ = ['GuiPluginLoader']

global_config_spec = ['dynamic_tuning = boolean(default=%s)'
                      % consts.CFG_DEF_DYNAMIC_TUNING,
                      'sleep_interval = integer(default=%s)'
                      % consts.CFG_DEF_SLEEP_INTERVAL,
                      'update_interval = integer(default=%s)'
                      % consts.CFG_DEF_UPDATE_INTERVAL]


class GuiPluginLoader():

    '''
    Class for scan, import and load actual avaible plugins.
    '''

    def __init__(self):
        '''
        Constructor
        '''

        self._plugins = {}
        self.plugins_doc = {}
        self._prefix = 'plugin_'
        self._sufix = '.py'
        self._dbus_controller = DBusController(consts.DBUS_BUS,
			consts.DBUS_INTERFACE, consts.DBUS_OBJECT
            )
        self._get_plugins()

    @property
    def plugins(self):
        return self._plugins

    def _get_plugins(self):
        self._plugins = self._dbus_controller.get_plugins()

    def get_plugin_doc(self, plugin_name):
        return self._dbus_controller.get_plugin_documentation(plugin_name)

    def get_plugin_hints(self, plugin_name):
        return self._dbus_controller.get_plugin_hints(plugin_name)

    def _load_global_config(self, file_name=consts.GLOBAL_CONFIG_FILE):
        """
        Loads global configuration file.
        """

        try:
            config = ConfigObj.ConfigObj(file_name,
                               configspec=global_config_spec,
                               raise_errors = True, file_error = True, list_values = False, interpolation = False)
        except IOError as e:
            raise TunedException("Global tuned configuration file '%s' not found."
                                  % file_name)
        except ConfigObj.ConfigObjError as e:
            raise TunedException("Error parsing global tuned configuration file '%s'."
                                  % file_name)
        vdt = Validator()
        if not config.validate(vdt, copy=True):
            raise TunedException("Global tuned configuration file '%s' is not valid."
                                  % file_name)
        return config


