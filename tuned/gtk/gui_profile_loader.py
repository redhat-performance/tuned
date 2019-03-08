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
Created on Mar 13, 2014

@author: mstana
'''

import os
import configobj
import subprocess
import json
import sys

import tuned.profiles.profile as p
import tuned.consts
import shutil
import tuned.gtk.managerException as managerException
import tuned.gtk.gui_profile_saver
import tuned.gtk.gui_profile_deleter

class GuiProfileLoader(object):

    """
    Profiles loader for GUI Gtk purposes.
    """

    profiles = {}

    def __init__(self, directories):
        self.directories = directories
        self._load_all_profiles()

    def get_raw_profile(self, profile_name):
        file = self._locate_profile_path(profile_name) + '/' \
            + profile_name + '/' + tuned.consts.PROFILE_FILE
        with open(file, 'r') as f:
            return f.read()

    def set_raw_profile(self, profile_name, config):

        profilePath = self._locate_profile_path(profile_name)

        config_lines = config.split('\n')

        if profilePath == tuned.consts.LOAD_DIRECTORIES[1]:
            file_path = profilePath + '/' + profile_name + '/' + tuned.consts.PROFILE_FILE

            config_obj = configobj.ConfigObj(infile=config_lines,list_values = False, interpolation = False)
            config_obj.filename = file_path
            config_obj.initial_comment = ('#', 'tuned configuration', '#')
            self._save_profile(config_obj)
            self._refresh_profiles()
        else:
            raise managerException.ManagerException(profile_name
                    + ' profile is stored in ' + profilePath
                    + ' and can not be storet do this location')

    def load_profile_config(self, profile_name, path):
        conf_path = path + '/' + profile_name + '/' + tuned.consts.PROFILE_FILE
        profile_config = configobj.ConfigObj(conf_path, list_values = False,
			interpolation = False)
        return profile_config

    def _locate_profile_path(self, profile_name):
        for d in self.directories:
            for profile in os.listdir(d):
                if os.path.isdir(d + '/' + profile) and profile \
                    == profile_name:
                    path = d
        return path

    def _load_all_profiles(self):
        for d in self.directories:
            for profile in os.listdir(d):
                if self._is_dir_profile(os.path.join(d, profile)):
                    try:
                        self.profiles[profile] = p.Profile(profile,
                                self.load_profile_config(profile, d))
                    except configobj.ParseError:
                        pass

#                         print "can not make \""+ profile +"\" profile without correct config on path: " + d
#                     except:
#                         raise managerException.ManagerException("Can not make profile")
#                         print "can not make \""+ profile +"\" profile without correct config with path: " + d

    def _is_dir_profile(self, path):
        return (os.path.isdir(path) and
                os.path.isfile(os.path.join(path, 'tuned.conf')))

    def _refresh_profiles(self):
        self.profiles = {}
        self._load_all_profiles()

    def save_profile(self, profile):
        path = tuned.consts.LOAD_DIRECTORIES[1] + '/' + profile.name
        config = configobj.ConfigObj(list_values = False, interpolation = False)
        config.filename = path + '/' + tuned.consts.PROFILE_FILE
        config.initial_comment = ('#', 'tuned configuration', '#')

        try:
            config['main'] = profile.options
        except KeyError:
            config['main'] = ''

            # profile dont have main section

            pass
        for (name, unit) in list(profile.units.items()):
            config[name] = unit.options

        self._save_profile(config)

        self._refresh_profiles()

    def update_profile(
        self,
        old_profile_name,
        profile,
        is_admin,
        ):

        if old_profile_name not in self.get_names():
            raise managerException.ManagerException('Profile: '
                    + old_profile_name + ' is not in profiles')

        path = tuned.consts.LOAD_DIRECTORIES[1] + '/' + profile.name

        if old_profile_name != profile.name:
            self.remove_profile(old_profile_name, is_admin=is_admin)

        config = configobj.ConfigObj(list_values = False, interpolation = False)
        config.filename = path + '/' + tuned.consts.PROFILE_FILE
        config.initial_comment = ('#', 'tuned configuration', '#')
        try:
            config['main'] = profile.options
        except KeyError:

            # profile dont have main section

            pass
        for (name, unit) in list(profile.units.items()):
            config[name] = unit.options

        self._save_profile(config)

        self._refresh_profiles()

    def get_names(self):
        self._refresh_profiles()
        return list(self.profiles.keys())

    def get_profile(self, profile):
        self._refresh_profiles()
        return self.profiles.get(profile, None)

    def add_profile(self, profile):
        self.profiles[profile.name] = profile
        self.save_profile(profile)

    def remove_profile(self, profile_name, is_admin):
        profile_path = self._locate_profile_path(profile_name)

        if self.is_profile_removable(profile_name):
            self._delete_profile(profile_name)
            self._load_all_profiles()
        else:
            raise managerException.ManagerException(profile_name
                    + ' profile is stored in ' + profile_path)

    def is_profile_removable(self, profile_name):

        #  profile is in /etc/profile

        profile_path = self._locate_profile_path(profile_name)
        if profile_path == tuned.consts.LOAD_DIRECTORIES[1]:
            return True
        else:
            return False

    def is_profile_factory(self, profile_name):

        #  profile is in /usr/lib/tuned

        return not self.is_profile_removable(profile_name)

    def _save_profile(self, config):
        ec = subprocess.call(['pkexec', sys.executable, tuned.gtk.gui_profile_saver.__file__ , json.dumps(config.__dict__)])
        if (ec != 0):
            raise managerException.ManagerException(
                'Error while saving profile file "%s"' % (config.filename))

    def _delete_profile(self, profile_name):
        ec = subprocess.call(['pkexec', sys.executable, tuned.gtk.gui_profile_deleter.__file__ , profile_name])
        if (ec != 0):
            raise managerException.ManagerException(
                'Error while deleting profile "%s"' % (profile_name))
