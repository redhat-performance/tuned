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

import os
import importlib
import inspect
from validate import Validator

import tuned.plugins.base
import tuned.consts as consts
import tuned.logs

import configobj as ConfigObj
from tuned.exceptions import TunedException

from tuned.utils.plugin_loader import PluginLoader
from tuned import plugins

__all__ = ['GuiPluginLoader']

global_config_spec = ['dynamic_tuning = boolean(default=%s)'
                      % consts.CFG_DEF_DYNAMIC_TUNING,
                      'sleep_interval = integer(default=%s)'
                      % consts.CFG_DEF_SLEEP_INTERVAL,
                      'update_interval = integer(default=%s)'
                      % consts.CFG_DEF_UPDATE_INTERVAL]


class GuiPluginLoader(PluginLoader):

    '''
    Class for scan, import and load actual avaible plugins.
    '''

    def __init__(self):
        '''
        Constructor
        '''

        self._plugins = []
        self.plugins_doc = {}
        self._prefix = 'plugin_'
        self._sufix = '.py'
        self._find_plugins()

    @property
    def plugins(self):
        return self._plugins

    def _find_plugins(self):
        for module_name in self._import_plugin_names():
            module = importlib.import_module('tuned.plugins.%s' % (module_name))
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj,tuned.plugins.base.Plugin):
                    self._plugins.append(obj)

    def _import_plugin_names(self):
        '''
        Scan directories and find names to load
        '''

        names = []
        for module_file in os.listdir(plugins.__path__[0]):
            if (module_file.startswith(self._prefix) and module_file.endswith(self._sufix)):
                names.append(module_file[:-3])
        return names

    def get_plugin(self, plugin_name):
        for plugin in self._plugins:
            if plugin_name == self.get_plugin_name(plugin):
                return plugin
        return None

    def get_plugin_name(self, plugin):
        return os.path.splitext(
            os.path.basename(inspect.getfile(plugin))[7:]
            )[0]

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


