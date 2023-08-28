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

import tuned.consts as consts
import tuned.logs
from tuned.utils.config_parser import ConfigParser, Error
from tuned.exceptions import TunedException
from tuned.utils.global_config import GlobalConfig

from tuned.admin.dbus_controller import DBusController

__all__ = ['GuiPluginLoader']


class GuiPluginLoader():

    '''
    Class for scan, import and load actual variable plugins.
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
            config_parser = ConfigParser(delimiters=('='), inline_comment_prefixes=('#'), strict=False)
            config_parser.optionxform = str
            with open(file_name) as f:
                config_parser.read_string("[" + consts.MAGIC_HEADER_NAME + "]\n" + f.read(), file_name)
            config, functions = GlobalConfig.get_global_config_spec()
            for option in config_parser.options(consts.MAGIC_HEADER_NAME):
                if option in config:
                    try:
                        func = getattr(config_parser, functions[option])
                        config[option] = func(consts.MAGIC_HEADER_NAME, option)
                    except Error:
                        raise TunedException("Global TuneD configuration file '%s' is not valid."
                                             % file_name)
                else:
                    config[option] = config_parser.get(consts.MAGIC_HEADER_NAME, option, raw=True)
        except IOError as e:
            raise TunedException("Global TuneD configuration file '%s' not found."
                                  % file_name)
        except Error as e:
            raise TunedException("Error parsing global TuneD configuration file '%s'."
                                  % file_name)
        return config

