#!/usr/bin/python
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

import os
import sys

import tuned.plugins.repository

from tuned.exceptions import TunedException


class Manager(object):

    def __init__(self):
        self.repository = tuned.plugins.repository.Repository()


if __name__ == '__main__':

    if os.geteuid() != 0:
        os.error('Superuser permissions are required to run the daemon.'
                 )
        sys.exit(1)

    man = Manager()
