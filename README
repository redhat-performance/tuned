Tuned: Daemon for monitoring and adaptive tuning of system devices.

(This is tuned 2.0 with a new code base. If you are looking for the older
version, please check out branch '1.0' in our Git repository.)

How to use it
-------------

In Fedora, Red Hat Enterprise Linux, and their derivates install tuned package
(optionally tuned-utils, tuned-utils-systemtap, and tuned-profiles-compat):

# yum install tuned

After the installation, start the tuned service:

# systemctl start tuned

You might also want to run tuned whenever your machine starts:

# systemctl enable tuned

If the daemon is running you can easily control it using 'tuned-adm' command
line utility. This tool communicates with the daemon over DBus. Any user can
list the available profiles and see which one is active. But the profiles can
be switched only by root user or by any user with physical console allocated
on the machine (X11, physical tty, but no SSH).

To see the current active profile, run:

$ tuned-adm active

To list all available profiles, run:

$ tuned-adm list

To switch to a different profile, run:

# tuned-adm profile <profile-name>

Your profile choice is also written into /etc/tuned/active_profile and this
choice is used when the daemon is restarted (e.g. with the machine reboot).

To disable all tunings, run:
# tuned-adm off

# tuned-adm recommend
Recommend profile suitable for your system. Currently only static detection is
implemented - it decides according to data in /etc/system-release-cpe and
virt-what output. The rules for autodetection are defined in the file
/usr/lib/tuned/recommend.d/50-tuned.conf. They can be overridden by the user by
putting a file to /etc/tuned/recommend.d or a file named recommend.conf into
/etc/tuned (see tuned-adm(8) for more details). The default rules recommend
profiles targeted to the best performance or the balanced profile if unsure.

Available tunings
-----------------

We are currenlty working on many new tuning features. Some are described in
the manual pages, some are yet undocumented.


Authors
-------

The best way to contact the authors of the project is to use our mailing list:
power-management@lists.fedoraproject.org

In case you want to contact individual author, you will find the e-mail
address in every commit message in our Git repository:
https://github.com/redhat-performance/tuned.git

You can also join #fedora-power IRC channel on Freenode.

Web page:
https://tuned-project.org/

Contributing
------------
See the file CONTRIBUTING.md for guidelines for contributing.

License
-------

Copyright (C) 2008-2019 Red Hat, Inc.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Full text of the license is enclosed in COPYING file.

The Developer Certificate of Origin, distributed in the file 'DCO' is licensed
differently, see the file for the text of the license.


The icon:

The Tuned icon was created by Mariia Leonova <mleonova@redhat.com> and it is
licensed under Creative Commons Attribution-ShareAlike 3.0 license
(http://creativecommons.org/licenses/by-sa/3.0/legalcode).
