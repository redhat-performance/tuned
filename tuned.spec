Summary: A dynamic adaptive system tuning daemon
Name: tuned
Version: 2.0
Release: 0.1.alpha%{?dist}
License: GPLv2
# The source for this package was pulled from upstream git.  Use the
# following commands to get the corresponding tarball:
#  git clone git://git.fedorahosted.org/git/tuned.git
#  cd tuned
#  git checkout v%{version}
#  make archive
Source: tuned-%{version}.tar.bz2
URL: https://fedorahosted.org/tuned/
BuildArch: noarch
BuildRequires: python, systemd-units
Requires(post): systemd-units
Requires(preun): systemd-units
Requires(postun): systemd-units

%description
The tuned package contains a daemon that tunes system settings dynamically.
It does so by monitoring the usage of several system components periodically.
Based on that information components will then be put into lower or higher
power saving modes to adapt to the current usage. Currently only ethernet
network and ATA harddisk devices are implemented.

%package utils
Summary: Disk and net statistic monitoring systemtap scripts
Requires: systemtap

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
make install DESTDIR=%{buildroot}


%post
# initial instalation
if [ $1 -eq 1 ]; then
	/usr/bin/systemctl daemon-reload &>/dev/null || :
fi


%preun
# package removal, not upgrade
if [ $1 -eq 0 ]; then
	/usr/bin/systemctl --no-reload disable tuned.service &>/dev/null || :
	/usr/bin/systemctl stop tuned.service &>/dev/null || :
fi


%postun
# package upgrade, not uninstall
if [ $1 -ge 1 ]; then
	/usr/bin/systemctl try-restart tuned.service &>/dev/null || :
fi


%triggerun -- tuned < 2.0-0
# remove ktune from old tuned, now part of tuned
/usr/sbin/service ktune stop &>/dev/null || :
/usr/sbin/chkconfig --del ktune &>/dev/null || :


%files
%defattr(-,root,root,-)
%doc AUTHORS ChangeLog COPYING INSTALL NEWS README doc/DESIGN.txt doc/TIPS.txt ktune/README.ktune doc/examples
%config(noreplace) %{_sysconfdir}/tuned.conf
%config(noreplace) %{_sysconfdir}/pam.d/tuned-adm
%config(noreplace) %{_sysconfdir}/security/console.apps/tuned-adm
%{_sysconfdir}/bash_completion.d
%{_sbindir}/tuned
%{_sbindir}/tuned-adm
# consolehelper hard link
%{_bindir}/tuned-adm
%config(noreplace) %{_sysconfdir}/tune-profiles/active-profile
%{_sysconfdir}/tune-profiles
%{_datadir}/tuned
%{_mandir}/man1/tuned-adm.*
%{_mandir}/man5/tuned.conf.*
%{_mandir}/man8/tuned.*
%config(noreplace) %{_sysconfdir}/sysconfig/ktune
%config(noreplace) %{_sysconfdir}/ktune.d/tunedadm.conf
%dir %{_sysconfdir}/ktune.d
%dir %{_localstatedir}/log/tuned
%dir %{_localstatedir}/run/tuned
%attr(0755,root,root) /lib/udev/tuned-mpath-iosched
/lib/udev/rules.d/*
%{_libexecdir}/tuned/
%if %uses_systemd
%{_sysconfdir}/tmpfiles.d
%{_unitdir}/tuned.service
# compatibility
%{_initddir}/ktune
%else
%{_initddir}/tuned
%{_initddir}/ktune
%endif

%files utils
%defattr(-,root,root,-)
%doc doc/README.utils
%doc doc/README.scomes
%doc COPYING
%{_sbindir}/varnetload
%{_sbindir}/netdevstat
%{_sbindir}/diskdevstat
%{_sbindir}/scomes
%{_mandir}/man8/varnetload.*
%{_mandir}/man8/netdevstat.*
%{_mandir}/man8/diskdevstat.*
%{_mandir}/man8/scomes.*


%changelog
* Mon Mar 12 2012 Jan Vcelak <jvcelak@redhat.com> 2.0-0.1.alpha
- brand new (pre)release of tuned
