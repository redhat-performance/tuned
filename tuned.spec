Summary: A adaptive dynamic system tuning daemon
Name: tuned
Version: 0.1.0
Release: 1%{?dist}
License: GPLv2+
Group: System Environment/Daemons
Source: tuned-%{version}.tar.bz2
Buildroot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch

%description
The tuned package contains a daemon that tunes system settings dynamically.

%package utils
Summary: Disk and net monitoring systemtap scripts
Requires: kernel-debuginfo
Group: Applications/System

%description utils
The tuned-utils package contains several systemtap scripts to allow detailed manual monitoring of the system.

%prep
%setup -q

%build

%install
rm -rf %{buildroot}
make install DESTDIR=%{buildroot}

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root)
%{bin}/tuned
%{datadir}/tuned.py
%{datadir}/monitorplugins
%{datadir}/tuningplugins

%files utils
%{_bin}/netdevstat
%{_bin}/diskdevstat


%changelog
* Thu Feb 19 2009 Phil Knirsch <pknirsch@redhat.com> - 0.1.0-1
- Initial version
