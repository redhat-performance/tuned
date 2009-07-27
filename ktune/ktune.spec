Summary: Server performance tuning service
Name: ktune
Version: 0.4
Release: 1%{?dist}
License: GPLv2
Group: System Environment/Base
URL: http://fedorahosted.org/ktune/
Source0: ktune.init
Source1: ktune.sysconfig
Source2: sysctl.ktune
Source3: COPYING
Source4: README
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
BuildArch: noarch
Requires(post): chkconfig
Requires(preun): chkconfig
Requires: gawk

%description
ktune provides settings for server performance tuning. Please have a look at 
%{_sysconfdir}/sysconfig/ktune and %{_sysconfdir}/sysctl.ktune for tuning 
parameters.

%prep

%build

%install
rm -rf $RPM_BUILD_ROOT
install -m 755 -d $RPM_BUILD_ROOT%{_sysconfdir}
install -m 644 %{SOURCE2} $RPM_BUILD_ROOT%{_sysconfdir}
install -m 755 -d $RPM_BUILD_ROOT%{_sysconfdir}/ktune.d
install -m 755 -d $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig
install -m 644 %{SOURCE1} $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig/ktune
install -m 755 -d $RPM_BUILD_ROOT%{_initrddir}
install -m 755 %{SOURCE0} $RPM_BUILD_ROOT%{_initrddir}/ktune

install -m 755 -d $RPM_BUILD_ROOT%{_docdir}/%{name}-%{version}
install -m 644 %{SOURCE3} $RPM_BUILD_ROOT%{_docdir}/%{name}-%{version}
install -m 644 %{SOURCE4} $RPM_BUILD_ROOT%{_docdir}/%{name}-%{version}

%clean
rm -rf $RPM_BUILD_ROOT

%post
/sbin/chkconfig --add ktune

%preun
if [ "$1" -eq 0 ]; then
	/sbin/service ktune stop >/dev/null 2>&1
	/sbin/chkconfig --del ktune
fi

%postun
if [ "$1" -eq 1 ]; then
	/sbin/service ktune condrestart >/dev/null 2>&1
fi

%files
%defattr(-,root,root,-)
%dir %attr(0755,root,root) %{_docdir}/%{name}-%{version}
%doc %attr(0644,root,root) %{_docdir}/%{name}-%{version}/COPYING
%doc %attr(0644,root,root) %{_docdir}/%{name}-%{version}/README
%attr(0755,root,root) %{_initrddir}/ktune
%config(noreplace) %attr(0644,root,root) %{_sysconfdir}/sysconfig/ktune
%config(noreplace) %attr(0644,root,root) %{_sysconfdir}/sysctl.ktune
%dir %attr(0755,root,root) %{_sysconfdir}/ktune.d

%changelog
* Fri Jul 24 2009 Thomas Woerner <twoerner@redhat.com> 0.3-2
- use /bin/ls with LANG=C

* Tue Jul 21 2009 Thomas Woerner <twoerner@redhat.com> 0.3-2
- added support for profile scripts

* Tue May  5 2008 Thomas Woerner <twoerner@redhat.com> 0.3-1
- added support for loading additional files: /etc/ktune.d/*.conf
  Resolves: rhbz#496940

* Wed Sep 17 2008 Thomas Woerner <twoerner@redhat.com> 0.2-3
- using dist tag

* Wed Sep 17 2008 Thomas Woerner <twoerner@redhat.com> 0.2-3
- service ktune should not be enabled by default
- new README and COPYING file
Resolves: rhbz#455399

* Fri Aug 29 2008 Thomas Woerner <twoerner@redhat.com> 0.2-2
- spec file changes according to rpmlint output

* Fri Aug 29 2008 Thomas Woerner <twoerner@redhat.com> 0.2-1
- new variable ELEVATOR_TUNE_DEVS in /etc/sysconfig/ktune to define the
  tunable devices, also tune cciss devices
- be more verbose for elevator settings
- added post and preun scripts

* Fri Aug 15 2008 Thomas Woerner <twoerner@redhat.com> 0.1-1
- Initial build.
