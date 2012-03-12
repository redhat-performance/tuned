Summary: A dynamic adaptive system tuning daemon
Name: tuned
Version: 2.0
Release: 0.1.alpha%{?dist}
License: GPLv2
# The source for this package was pulled from upstream git.  Use the
# following commands to get the corresponding tarball:
#  git clone git://git.fedorahosted.org/git/tuned.git
#  cd tuned
#  git checkout v%%{version}
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
%doc AUTHORS
%doc COPYING
%doc README
%doc doc/TIPS.txt
%{python_sitelib}/tuned
%{_sbindir}/tuned
%{_prefix}/lib/tuned
%config(noreplace) %{_sysconfdir}/tuned/active_profile
%{_sysconfdir}/tmpfiles.d
%{_unitdir}/tuned.service
%dir %{_localstatedir}/log/tuned
%dir %{_localstatedir}/run/tuned

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
