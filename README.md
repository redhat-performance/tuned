# TuneD: Daemon for monitoring and adaptive tuning of system devices.

(This is TuneD 2.0 with a new code base. If you are looking for the older
version, please check out branch '1.0' in our Git repository.)

How to use it
-------------

TuneD is incompatible with ``cpupower`` and ``power-profiles-daemon``. If you
have these services, uninstall or disable them.

On Fedora, Red Hat Enterprise Linux, and their derivatives: install the ``tuned`` package
(optionally ``tuned-utils``, ``tuned-utils-systemtap``, and ``tuned-profiles-compat``):

```bash
  # dnf install tuned
```

After installation, start the ``tuned`` service:

```bash
  # systemctl start tuned
```

You likely should run ``tuned`` whenever your machine boots:

```bash
  # systemctl enable tuned
```

When the daemon is running you can easily control it using the ``tuned-adm``
utility. This tool communicates with the daemon over DBus. Any user can
list the available profiles and see which one is active. The active profile can
be switched only by root user or by any user with physical console allocated
on the machine (X11, physical tty, but no SSH).

To see the current active profile, run:

```bash
  # tuned-adm active
```

To list all available profiles, run:

```bash
  # tuned-adm list
```

To switch to a different profile, run:

```bash
  # tuned-adm profile <profile-name>
```

The enabled profile is persisted into ``/etc/tuned/active_profile``, which
is read when the daemon starts or is restarted.

To disable all tunings, run:

```bash
  # tuned-adm off
```

To show information/description of given profile or current profile if no profile is specified, run:

```bash
  # tuned-adm profile_info
```

To verify current profile against system settings, run:

```bash
  # tuned-adm verify
```

To enable automatic profile selection, run:

```bash
  # tuned-adm auto_profile
```

To show the current profile selection mode, run:

```bash
  # tuned-adm profile_mode
```

To recommend a profile for a given system, run:

```bash
  # tuned-adm recommend
```
Currently only static detection is
implemented - it decides according to data in ``/etc/system-release-cpe`` and
the output of ``virt-what``. The rules for autodetection are defined in the file
``/usr/lib/tuned/recommend.d/50-tuned.conf``. They can be overridden by the user by
creating a file in ``/etc/tuned/recommend.d`` or a file named ``recommend.conf`` in
``/etc/tuned``.  See the ``tuned-adm(8)`` man page for details). The default rules
recommend profiles targeted to the best performance or the balanced profile if unsure.

Available tunings
-----------------

We are currently working on many new tuning features. Some are described in
the manual pages, some are yet undocumented.


Authors
-------

The best way to contact the authors of the project is to use our mailing list:
<power-management@lists.fedoraproject.org>

If you want to contact an individual author, you will find their e-mail
address in every commit message in our Git repository:
<https://github.com/redhat-performance/tuned.git>

You can also join the ``#fedora-power`` IRC channel on Freenode.

Web page:
<https://tuned-project.org/>

Contributing
------------
See the file ``CONTRIBUTING.md`` for guidelines for contributing.

License
-------

Copyright (C) 2008-2021 Red Hat, Inc.

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

The TuneD icon was created by Mariia Leonova <mleonova@redhat.com> and it is
licensed under Creative Commons Attribution-ShareAlike 3.0 license
(http://creativecommons.org/licenses/by-sa/3.0/legalcode).
