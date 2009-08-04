Summary: A dynamic adaptive system tuning daemon
Name: tuned
Version: 0.2.1
Release: 1%{?dist}
License: GPLv2+
Group: System Environment/Daemons
# The source for this package was pulled from upstream git.  Use the
# following commands to get the corresponding tarball:
#  git clone git://fedorapeople.org/~pknirsch/tuned.git/
#  cd tuned
#  git checkout v%{version}
#  make archive
Source: tuned-%{version}.tar.bz2
URL: http://fedorapeople.org/~pknirsch/git/tuned.git/
Buildroot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
Requires(post): chkconfig
Requires(preun): chkconfig
Requires(preun): initscripts
Requires(postun): initscripts
BuildArch: noarch
Requires: kobo

%description
The tuned package contains a daemon that tunes system settings dynamically.
It does so by monitoring the usage of several system components periodically.
Based on that information components will then be put into lower or higher
power saving modes to adapt to the current usage. Currently only ethernet
network and ATA harddisk devices are implemented.

%package utils
Summary: Disk and net statistic monitoring systemtap scripts
Requires: systemtap
Group: Applications/System

%description utils
The tuned-utils package contains several systemtap scripts to allow detailed
manual monitoring of the system. Instead of the typical IO/sec it collects
minimal, maximal and average time between operations to be able to
identify applications that behave power inefficient (many small operations
instead of fewer large ones).

%prep
%setup -q

%build

%install
rm -rf %{buildroot}
make install DESTDIR=%{buildroot}

%clean
rm -rf %{buildroot}

%post
/sbin/chkconfig --add tuned
/sbin/chkconfig --add ktune

%preun
if [ $1 = 0 ] ; then
    /sbin/service tuned stop >/dev/null 2>&1
    /sbin/chkconfig --del tuned
    /sbin/service ktune stop >/dev/null 2>&1
    /sbin/chkconfig --del ktune
fi

%postun
if [ "$1" -ge "1" ] ; then
    /sbin/service tuned condrestart >/dev/null 2>&1 || :
    /sbin/service ktune condrestart >/dev/null 2>&1 || :
fi

%files
%defattr(-,root,root,-)
%doc AUTHORS ChangeLog COPYING INSTALL NEWS README doc/DESIGN.txt doc/TIPS.txt ktune/README.ktune
%{_initddir}/tuned
%config(noreplace) %{_sysconfdir}/tuned.conf
%{_sbindir}/tuned
%{_sbindir}/tuned-adm
%{_sysconfdir}/tune-profiles
%{_datadir}/tuned
%{_mandir}/man5/*
%{_mandir}/man8/*
%attr(0755,root,root) %{_initddir}/ktune
%config(noreplace) %attr(0644,root,root) %{_sysconfdir}/sysconfig/ktune
%config(noreplace) %attr(0644,root,root) %{_sysconfdir}/sysctl.ktune
%dir %attr(0755,root,root) %{_sysconfdir}/ktune.d

%files utils
%defattr(-,root,root,-)
%doc doc/README.utils
%doc doc/README.scomes
%{_sbindir}/varnetload
%{_sbindir}/netdevstat
%{_sbindir}/diskdevstat
%{_sbindir}/scomes


%changelog
* Tue Aug 04 2009 Phil Knirsch <pknirsch@redhat.com> - 0.2.1-1
- Added first set of profiles
- Added tuned-adm tool for profile switching
- Fixed several issues with the tuned-adm tool

* Mon Jul 27 2009 Thomas Woerner <twoerner@redhat.com> - 0.2.0-1
- Integrated ktune-0.4

* Thu Jul 16 2009 Phil Knirsch <pknirsch@redhat.com> - 0.1.7-1
- Added first version CPU tuning and monitoring plugins

* Thu Jun 25 2009 Petr Lautrbach <plautrba@redhat.com> - 0.1.6-1
- added scomes

* Wed Mar 25 2009 Phil Knirsch <pknirsch@redhat.com> - 0.1.5-1
- Updated documentation, thanks to Marcela Maslanova!
- Updated diskdevstat and netdevstat to have command line arguments
- Added the possibility to output a histogram at the end of the
  run for detailed information about the collected data

* Fri Mar 06 2009 Phil Knirsch <pknirsch@redhat.com> - 0.1.4-1
- Dropped unecessary kernel-debuginfo requires from tuned-utils

* Mon Mar 02 2009 Phil Knirsch <pknirsch@redhat.com> - 0.1.3-1
- Fixed placement of doc entry at tuned-utils package

* Thu Feb 26 2009 Phil Knirsch <pknirsch@redhat.com> - 0.1.2-1
- Added config file option to enable/disable plugins
- Switched from ConfigParser to RawConfigParser
- Renamed doc/README.txt to doc/DESIGN.txt
- Added tuned.conf man page
- Updated tuned man page
- Updated package descriptions (#487312)
- Added documentation for utils scripts (#487312)

* Wed Feb 25 2009 Phil Knirsch <pknirsch@redhat.com> - 0.1.1-1
- Bump version
- Added comment in empty __init__.py files
- Fixed BuildRoot tag to use latest recommendation of FPG
- Lots of whitespace changes
- Some minor README changes
- Added a changelog rule in Makefile
- Fixed rpmlint error messages
- Add init() methods to each plugin
- Call plugin init() methods during tuned's init()
- Add support for command line parameters
      o -c conffile|--config==conffile to specify the location of the config file
      o -d to start tuned as a daemon (instead of as normal app)
- Readded the debug output in case tuned isn't started as as daemon
- Fixed initialization of max transfer values for net tuning plugin
- Added complete cleanup code in case of tuned exiting and/or
  getting a SIGTERM to restore default values
- Made the disk tuning pluging less nosy if started as non-daemon
- Fixed missing self. in the tuned.py config handling
- Added a manpage
- Fixed summary
- Added missing GPL notic to tuned.py
- Added explanation for Source entry in specfile
- Added a distarchive target for the Makefile for proper tagging in git
- Added a explanation how to create the tarball via git in the specfile
- Fixed the defattr() lines in the specfile to conform FRG

* Mon Feb 23 2009 Phil Knirsch <pknirsch@redhat.com> - 0.1.0-1
- Initial version
