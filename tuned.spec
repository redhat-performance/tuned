%bcond_with snapshot

%if 0%{?fedora}
%if 0%{?fedora} > 27
%bcond_without python3
%else
%bcond_with python3
%endif
%else
%if 0%{?rhel} && 0%{?rhel} < 8
%bcond_with python3
%else
%bcond_without python3
%endif
%endif

%if %{with python3}
%global _py python3
%global make_python_arg PYTHON=%{__python3}
%else
%{!?python2_sitelib:%global python2_sitelib %{python_sitelib}}
%if 0%{?rhel} && 0%{?rhel} < 8
%global make_python_arg PYTHON=%{__python}
%global _py python
%else
%global make_python_arg PYTHON=%{__python2}
%global _py python2
%endif
%endif

%if %{with snapshot}
%if 0%{!?git_short_commit:1}
%global git_short_commit %(git rev-parse --short=8 --verify HEAD)
%endif
%global git_date %(date +'%Y%m%d')
%global git_suffix %{git_date}git%{git_short_commit}
%endif

#%%global prerelease rc
#%%global prereleasenum 1

%global prerel1 %{?prerelease:.%{prerelease}%{prereleasenum}}
%global prerel2 %{?prerelease:-%{prerelease}.%{prereleasenum}}

Summary: A dynamic adaptive system tuning daemon
Name: tuned
Version: 2.24.0
Release: 1%{?prerel1}%{?with_snapshot:.%{git_suffix}}%{?dist}
License: GPL-2.0-or-later AND CC-BY-SA-3.0
Source0: https://github.com/redhat-performance/%{name}/archive/v%{version}%{?prerel2}/%{name}-%{version}%{?prerel2}.tar.gz
URL: http://www.tuned-project.org/
BuildArch: noarch
BuildRequires: systemd, desktop-file-utils
%if 0%{?rhel}
BuildRequires: asciidoc
%else
BuildRequires: asciidoctor
%endif
Requires(post): systemd, virt-what
Requires(preun): systemd
Requires(postun): systemd
BuildRequires: make
BuildRequires: %{_py}, %{_py}-devel
# BuildRequires for 'make test'
# python-mock is needed for python-2.7, but it's not available on RHEL-7, only in the EPEL
%if %{without python3} && ( ! 0%{?rhel} || 0%{?rhel} >= 8 || 0%{?epel})
BuildRequires: %{_py}-mock
%endif
BuildRequires: %{_py}-pyudev
Requires: %{_py}-pyudev
Requires: %{_py}-linux-procfs, %{_py}-perf
%if %{without python3}
Requires: %{_py}-schedutils
%endif
# requires for packages with inconsistent python2/3 names
%if %{with python3}
# BuildRequires for 'make test'
BuildRequires: python3-dbus, python3-gobject-base
Requires: python3-dbus, python3-gobject-base
%if 0%{?fedora} > 22 || 0%{?rhel} > 7
Recommends: dmidecode
%endif
%else
# BuildRequires for 'make test'
BuildRequires: dbus-python, pygobject3-base
Requires: dbus-python, pygobject3-base
%endif
Requires: virt-what, ethtool, gawk
Requires: util-linux, dbus, polkit
%if 0%{?fedora} > 22 || 0%{?rhel} > 7
Recommends: dmidecode
# i686 excluded
Recommends: kernel-tools
Requires: hdparm
Requires: kmod
Requires: iproute
%endif
# syspurpose
%if 0%{?rhel} > 8
# not on CentOS
%if 0%{!?centos:1}
Recommends: subscription-manager
%endif
%else
%if 0%{?rhel} > 7
Requires: python3-syspurpose
%endif
%endif

%description
The tuned package contains a daemon that tunes system settings dynamically.
It does so by monitoring the usage of several system components periodically.
Based on that information components will then be put into lower or higher
power saving modes to adapt to the current usage. Currently only ethernet
network and ATA harddisk devices are implemented.

%if 0%{?rhel} <= 7 && 0%{!?fedora:1}
# RHEL <= 7
%global docdir %{_docdir}/%{name}-%{version}
%else
# RHEL > 7 || fedora
%global docdir %{_docdir}/%{name}
%endif

%package gtk
Summary: GTK GUI for tuned
Requires: %{name} = %{version}-%{release}
Requires: powertop, polkit
# requires for packages with inconsistent python2/3 names
%if %{with python3}
Requires: python3-gobject-base
%else
Requires: pygobject3-base
%endif

%description gtk
GTK GUI that can control tuned and provides simple profile editor.

%package utils
Requires: %{name} = %{version}-%{release}
Requires: powertop
Summary: Various tuned utilities

%description utils
This package contains utilities that can help you to fine tune and
debug your system and manage tuned profiles.

%package utils-systemtap
Summary: Disk and net statistic monitoring systemtap scripts
Requires: %{name} = %{version}-%{release}
Requires: systemtap

%description utils-systemtap
This package contains several systemtap scripts to allow detailed
manual monitoring of the system. Instead of the typical IO/sec it collects
minimal, maximal and average time between operations to be able to
identify applications that behave power inefficient (many small operations
instead of fewer large ones).

%package profiles-sap
Summary: Additional tuned profile(s) targeted to SAP NetWeaver loads
Requires: %{name} = %{version}

%description profiles-sap
Additional tuned profile(s) targeted to SAP NetWeaver loads.

%package profiles-mssql
Summary: Additional tuned profile(s) for MS SQL Server
Requires: %{name} = %{version}

%description profiles-mssql
Additional tuned profile(s) for MS SQL Server.

%package profiles-oracle
Summary: Additional tuned profile(s) targeted to Oracle loads
Requires: %{name} = %{version}

%description profiles-oracle
Additional tuned profile(s) targeted to Oracle loads.

%package profiles-sap-hana
Summary: Additional tuned profile(s) targeted to SAP HANA loads
Requires: %{name} = %{version}

%description profiles-sap-hana
Additional tuned profile(s) targeted to SAP HANA loads.

%package profiles-atomic
Summary: Additional tuned profile(s) targeted to Atomic
Requires: %{name} = %{version}

%description profiles-atomic
Additional tuned profile(s) targeted to Atomic host and guest.

%package profiles-realtime
Summary: Additional tuned profile(s) targeted to realtime
Requires: %{name} = %{version}
Requires: tuna

%description profiles-realtime
Additional tuned profile(s) targeted to realtime.

%package profiles-nfv-guest
Summary: Additional tuned profile(s) targeted to Network Function Virtualization (NFV) guest
Requires: %{name} = %{version}
Requires: %{name}-profiles-realtime = %{version}
Requires: tuna

%description profiles-nfv-guest
Additional tuned profile(s) targeted to Network Function Virtualization (NFV) guest.

%package profiles-nfv-host
Summary: Additional tuned profile(s) targeted to Network Function Virtualization (NFV) host
Requires: %{name} = %{version}
Requires: %{name}-profiles-realtime = %{version}
Requires: tuna

%description profiles-nfv-host
Additional tuned profile(s) targeted to Network Function Virtualization (NFV) host.

# this is kept for backward compatibility, it should be dropped for RHEL-8
%package profiles-nfv
Summary: Additional tuned profile(s) targeted to Network Function Virtualization (NFV)
Requires: %{name} = %{version}
Requires: %{name}-profiles-nfv-guest = %{version}
Requires: %{name}-profiles-nfv-host = %{version}

%description profiles-nfv
Additional tuned profile(s) targeted to Network Function Virtualization (NFV).

%package profiles-cpu-partitioning
Summary: Additional tuned profile(s) optimized for CPU partitioning
Requires: %{name} = %{version}

%description profiles-cpu-partitioning
Additional tuned profile(s) optimized for CPU partitioning.

%package profiles-spectrumscale
Summary: Additional tuned profile(s) optimized for IBM Spectrum Scale
Requires: %{name} = %{version}

%description profiles-spectrumscale
Additional tuned profile(s) optimized for IBM Spectrum Scale.

%package profiles-compat
Summary: Additional tuned profiles mainly for backward compatibility with tuned 1.0
Requires: %{name} = %{version}

%description profiles-compat
Additional tuned profiles mainly for backward compatibility with tuned 1.0.
It can be also used to fine tune your system for specific scenarios.

%package profiles-postgresql
Summary: Additional tuned profile(s) targeted to PostgreSQL server loads
Requires: %{name} = %{version}

%description profiles-postgresql
Additional tuned profile(s) targeted to PostgreSQL server loads.

%package profiles-openshift
Summary: Additional TuneD profile(s) optimized for OpenShift
Requires: %{name} = %{version}

%description profiles-openshift
Additional TuneD profile(s) optimized for OpenShift.

%package ppd
Summary: PPD compatibility daemon
Requires: %{name} = %{version}
# The compatibility daemon is swappable for power-profiles-daemon
Provides: ppd-service
Conflicts: ppd-service

%description ppd
An API translation daemon that allows applications to easily transition
to TuneD from power-profiles-daemon (PPD).

%prep
%autosetup -p1 -n %{name}-%{version}%{?prerel2}

%build
# Docs cannot be generated on RHEL now due to missing asciidoctor dependency
# asciidoc doesn't seem to be compatible
%if ! 0%{?rhel}
make html %{make_python_arg}
%endif

%install
make install DESTDIR=%{buildroot} DOCDIR=%{docdir} %{make_python_arg}
make install-ppd DESTDIR=%{buildroot} DOCDIR=%{docdir} %{make_python_arg}

%if ! 0%{?rhel}
# manual
make install-html DESTDIR=%{buildroot} DOCDIR=%{docdir}
%endif

# conditional support for grub2, grub2 is not available on all architectures
# and tuned is noarch package, thus the following hack is needed
mkdir -p %{buildroot}%{_datadir}/tuned/grub2
mv %{buildroot}%{_sysconfdir}/grub.d/00_tuned %{buildroot}%{_datadir}/tuned/grub2/00_tuned
rmdir %{buildroot}%{_sysconfdir}/grub.d

# ghost for persistent storage
mkdir -p %{buildroot}%{_var}/lib/tuned

# ghost for NFV
mkdir -p %{buildroot}%{_sysconfdir}/modprobe.d
touch %{buildroot}%{_sysconfdir}/modprobe.d/kvm.rt.tuned.conf

# validate desktop file
desktop-file-validate %{buildroot}%{_datadir}/applications/tuned-gui.desktop

# On RHEL-7 EPEL is needed, because there is no python-mock package and
# python-2.7 doesn't have mock built-in
%if 0%{?rhel} >= 8 || 0%{?epel} || ! 0%{?rhel}
%check
make test %{make_python_arg}
%endif

%post
%systemd_post tuned.service

# convert active_profile from full path to name (if needed)
sed -i 's|.*/\([^/]\+\)/[^\.]\+\.conf|\1|' /etc/tuned/active_profile

# convert GRUB_CMDLINE_LINUX to GRUB_CMDLINE_LINUX_DEFAULT
if [ -r "%{_sysconfdir}/default/grub" ]; then
  sed -i 's/GRUB_CMDLINE_LINUX="$GRUB_CMDLINE_LINUX \\$tuned_params"/GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT \\$tuned_params"/' \
    %{_sysconfdir}/default/grub
fi

%if 0%{?fedora} || 0%{?rhel} >= 10
# migrate all user-defined profiles from /etc/tuned/ to /etc/tuned/profiles/
for f in %{_sysconfdir}/tuned/*; do
  if [ -e "$f/tuned.conf" ]; then
    mv -n "$f" %{_sysconfdir}/tuned/profiles/
  fi
done
%endif


%post ppd
%systemd_post tuned-ppd.service


%preun
%systemd_preun tuned.service
if [ "$1" == 0 ]; then
# clear persistent storage
  rm -f %{_var}/lib/tuned/*
# clear temporal storage
  rm -f /run/tuned/*
fi


%preun ppd
%systemd_preun tuned-ppd.service


%postun
%systemd_postun_with_restart tuned.service

# conditional support for grub2, grub2 is not available on all architectures
# and tuned is noarch package, thus the following hack is needed
if [ "$1" == 0 ]; then
  rm -f %{_sysconfdir}/grub.d/00_tuned || :
# unpatch /etc/default/grub
  if [ -r "%{_sysconfdir}/default/grub" ]; then
    sed -i '/GRUB_CMDLINE_LINUX_DEFAULT="${GRUB_CMDLINE_LINUX_DEFAULT:+$GRUB_CMDLINE_LINUX_DEFAULT }\\$tuned_params"/d' %{_sysconfdir}/default/grub
  fi

# cleanup for Boot loader specification (BLS)

# clear grubenv variables
  grub2-editenv - unset tuned_params tuned_initrd &>/dev/null || :
# unpatch BLS entries
  MACHINE_ID=`cat /etc/machine-id 2>/dev/null`
  if [ "$MACHINE_ID" ]
  then
    for f in /boot/loader/entries/$MACHINE_ID-*.conf
    do
      # Skip non-files and rescue entries
      if [ ! -f "$f" -o "${f: -12}" == "-rescue.conf" ]
      then
        continue
      fi
      # Skip boom managed entries
      if [[ "$f" =~ \w*-[0-9a-f]{7,}-.*-.*.conf ]]
      then
        continue
      fi
      sed -i '/^\s*options\s\+.*\$tuned_params/ s/\s\+\$tuned_params\b//g' "$f" &>/dev/null || :
      sed -i '/^\s*initrd\s\+.*\$tuned_initrd/ s/\s\+\$tuned_initrd\b//g' "$f" &>/dev/null || :
    done
  fi
fi


%postun ppd
%systemd_postun_with_restart tuned-ppd.service


%triggerun -- tuned < 2.0-0
# remove ktune from old tuned, now part of tuned
/usr/sbin/service ktune stop &>/dev/null || :
/usr/sbin/chkconfig --del ktune &>/dev/null || :


%triggerun ppd -- power-profiles-daemon
# if swapping power-profiles-daemon for tuned-ppd, check whether it is active
if systemctl is-active --quiet power-profiles-daemon; then
  mkdir -p %{_localstatedir}/lib/rpm-state/tuned
  touch %{_localstatedir}/lib/rpm-state/tuned/ppd-active
fi


%posttrans
# conditional support for grub2, grub2 is not available on all architectures
# and tuned is noarch package, thus the following hack is needed
if [ -d %{_sysconfdir}/grub.d ]; then
  cp -a %{_datadir}/tuned/grub2/00_tuned %{_sysconfdir}/grub.d/00_tuned
  selinuxenabled &>/dev/null && \
    restorecon %{_sysconfdir}/grub.d/00_tuned &>/dev/null || :
fi


%posttrans ppd
# if power-profiles-daemon was active before installing tuned-ppd,
# start tuned-ppd right away
if [ -f %{_localstatedir}/lib/rpm-state/tuned/ppd-active ]; then
  systemctl start tuned-ppd
  rm -rf %{_localstatedir}/lib/rpm-state/tuned
fi


%files
%exclude %{docdir}/README.utils
%exclude %{docdir}/README.scomes
%exclude %{docdir}/README.NFV
%doc %{docdir}
%{_datadir}/bash-completion/completions/tuned-adm
%if %{with python3}
%exclude %{python3_sitelib}/tuned/gtk
%{python3_sitelib}/tuned
%else
%exclude %{python2_sitelib}/tuned/gtk
%{python2_sitelib}/tuned
%endif
%{_sbindir}/tuned
%{_sbindir}/tuned-adm
%exclude %{_sysconfdir}/tuned/realtime-variables.conf
%exclude %{_sysconfdir}/tuned/realtime-virtual-guest-variables.conf
%exclude %{_sysconfdir}/tuned/realtime-virtual-host-variables.conf
%exclude %{_sysconfdir}/tuned/cpu-partitioning-variables.conf
%exclude %{_sysconfdir}/tuned/cpu-partitioning-powersave-variables.conf
%exclude %{_prefix}/lib/tuned/profiles/default
%exclude %{_prefix}/lib/tuned/profiles/desktop-powersave
%exclude %{_prefix}/lib/tuned/profiles/laptop-ac-powersave
%exclude %{_prefix}/lib/tuned/profiles/server-powersave
%exclude %{_prefix}/lib/tuned/profiles/laptop-battery-powersave
%exclude %{_prefix}/lib/tuned/profiles/enterprise-storage
%exclude %{_prefix}/lib/tuned/profiles/spindown-disk
%exclude %{_prefix}/lib/tuned/profiles/sap-netweaver
%exclude %{_prefix}/lib/tuned/profiles/sap-hana
%exclude %{_prefix}/lib/tuned/profiles/sap-hana-kvm-guest
%exclude %{_prefix}/lib/tuned/profiles/mssql
%exclude %{_prefix}/lib/tuned/profiles/oracle
%exclude %{_prefix}/lib/tuned/profiles/atomic-host
%exclude %{_prefix}/lib/tuned/profiles/atomic-guest
%exclude %{_prefix}/lib/tuned/profiles/realtime
%exclude %{_prefix}/lib/tuned/profiles/realtime-virtual-guest
%exclude %{_prefix}/lib/tuned/profiles/realtime-virtual-host
%exclude %{_prefix}/lib/tuned/profiles/cpu-partitioning
%exclude %{_prefix}/lib/tuned/profiles/cpu-partitioning-powersave
%exclude %{_prefix}/lib/tuned/profiles/spectrumscale-ece
%exclude %{_prefix}/lib/tuned/profiles/postgresql
%exclude %{_prefix}/lib/tuned/profiles/openshift
%exclude %{_prefix}/lib/tuned/profiles/openshift-control-plane
%exclude %{_prefix}/lib/tuned/profiles/openshift-node
%{_prefix}/lib/tuned
%dir %{_sysconfdir}/tuned
%dir %{_sysconfdir}/tuned/recommend.d
%dir %{_sysconfdir}/tuned/profiles
%dir %{_libexecdir}/tuned
%{_libexecdir}/tuned/defirqaffinity*
%config(noreplace) %verify(not size mtime md5) %{_sysconfdir}/tuned/active_profile
%config(noreplace) %verify(not size mtime md5) %{_sysconfdir}/tuned/profile_mode
%config(noreplace) %verify(not size mtime md5) %{_sysconfdir}/tuned/post_loaded_profile
%config(noreplace) %verify(not size mtime md5) %{_sysconfdir}/tuned/ppd_base_profile
%config(noreplace) %{_sysconfdir}/tuned/tuned-main.conf
%config(noreplace) %verify(not size mtime md5) %{_sysconfdir}/tuned/bootcmdline
%verify(not size mtime md5) %{_sysconfdir}/modprobe.d/tuned.conf
%{_tmpfilesdir}/tuned.conf
%{_unitdir}/tuned.service
%dir %{_localstatedir}/log/tuned
%dir /run/tuned
%dir %{_var}/lib/tuned
%{_mandir}/man5/tuned*
%{_mandir}/man7/tuned-profiles.7*
%{_mandir}/man8/tuned*
%dir %{_datadir}/tuned
%{_datadir}/tuned/grub2
%{_datadir}/dbus-1/system.d/com.redhat.tuned.conf
%{_datadir}/polkit-1/actions/com.redhat.tuned.policy
%ghost %{_sysconfdir}/modprobe.d/kvm.rt.tuned.conf
%{_prefix}/lib/kernel/install.d/92-tuned.install

%files gtk
%{_sbindir}/tuned-gui
%if %{with python3}
%{python3_sitelib}/tuned/gtk
%else
%{python2_sitelib}/tuned/gtk
%endif
%{_datadir}/tuned/ui
%{_datadir}/icons/hicolor/scalable/apps/tuned.svg
%{_datadir}/applications/tuned-gui.desktop

%files utils
%doc COPYING
%{_bindir}/powertop2tuned
%{_libexecdir}/tuned/pmqos-static*

%files utils-systemtap
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

%files profiles-sap
%{_prefix}/lib/tuned/profiles/sap-netweaver
%{_mandir}/man7/tuned-profiles-sap.7*

%files profiles-sap-hana
%{_prefix}/lib/tuned/profiles/sap-hana
%{_prefix}/lib/tuned/profiles/sap-hana-kvm-guest
%{_mandir}/man7/tuned-profiles-sap-hana.7*

%files profiles-mssql
%{_prefix}/lib/tuned/profiles/mssql
%{_mandir}/man7/tuned-profiles-mssql.7*

%files profiles-oracle
%{_prefix}/lib/tuned/profiles/oracle
%{_mandir}/man7/tuned-profiles-oracle.7*

%files profiles-atomic
%{_prefix}/lib/tuned/profiles/atomic-host
%{_prefix}/lib/tuned/profiles/atomic-guest
%{_mandir}/man7/tuned-profiles-atomic.7*

%files profiles-realtime
%config(noreplace) %{_sysconfdir}/tuned/realtime-variables.conf
%{_prefix}/lib/tuned/profiles/realtime
%{_mandir}/man7/tuned-profiles-realtime.7*

%files profiles-nfv-guest
%config(noreplace) %{_sysconfdir}/tuned/realtime-virtual-guest-variables.conf
%{_prefix}/lib/tuned/profiles/realtime-virtual-guest
%{_mandir}/man7/tuned-profiles-nfv-guest.7*

%files profiles-nfv-host
%config(noreplace) %{_sysconfdir}/tuned/realtime-virtual-host-variables.conf
%{_prefix}/lib/tuned/profiles/realtime-virtual-host
%{_mandir}/man7/tuned-profiles-nfv-host.7*

%files profiles-nfv
%doc %{docdir}/README.NFV

%files profiles-cpu-partitioning
%config(noreplace) %{_sysconfdir}/tuned/cpu-partitioning-variables.conf
%config(noreplace) %{_sysconfdir}/tuned/cpu-partitioning-powersave-variables.conf
%{_prefix}/lib/tuned/profiles/cpu-partitioning
%{_prefix}/lib/tuned/profiles/cpu-partitioning-powersave
%{_mandir}/man7/tuned-profiles-cpu-partitioning.7*

%files profiles-spectrumscale
%{_prefix}/lib/tuned/profiles/spectrumscale-ece
%{_mandir}/man7/tuned-profiles-spectrumscale-ece.7*

%files profiles-compat
%{_prefix}/lib/tuned/profiles/default
%{_prefix}/lib/tuned/profiles/desktop-powersave
%{_prefix}/lib/tuned/profiles/laptop-ac-powersave
%{_prefix}/lib/tuned/profiles/server-powersave
%{_prefix}/lib/tuned/profiles/laptop-battery-powersave
%{_prefix}/lib/tuned/profiles/enterprise-storage
%{_prefix}/lib/tuned/profiles/spindown-disk
%{_mandir}/man7/tuned-profiles-compat.7*

%files profiles-postgresql
%{_prefix}/lib/tuned/profiles/postgresql
%{_mandir}/man7/tuned-profiles-postgresql.7*

%files profiles-openshift
%{_prefix}/lib/tuned/profiles/openshift
%{_prefix}/lib/tuned/profiles/openshift-control-plane
%{_prefix}/lib/tuned/profiles/openshift-node
%{_mandir}/man7/tuned-profiles-openshift.7*

%files ppd
%{_sbindir}/tuned-ppd
%{_unitdir}/tuned-ppd.service
%{_datadir}/dbus-1/system-services/net.hadess.PowerProfiles.service
%{_datadir}/dbus-1/system.d/net.hadess.PowerProfiles.conf
%{_datadir}/polkit-1/actions/net.hadess.PowerProfiles.policy
%config(noreplace) %{_sysconfdir}/tuned/ppd.conf

%changelog
* Wed Aug  7 2024 Jaroslav Škarvada <jskarvad@redhat.com> - 2.24.0-1
- new release
  - clear plugin repository when stopping tuning
    resolves: RHEL-36442
  - man: add description of the balanced-battery profile

* Thu Jul 25 2024 Jaroslav Škarvada <jskarvad@redhat.com> - 2.24.0-0.1.rc1
- new release
  - hotplug: wait for device initialization
    resolves: RHEL-39468
  - functions: added 'package2cpus' and 'packages2uncores' matchers
  - functions: added 'lscpu' to list CPU details
  - plugin_uncore: allow to configure frequency limits using percent
  - amd-pstate: added support for controlling core performance boost
  - plugin_scheduler: adjusted error logging in _set_affinity
    resolves: RHEL-46560
  - plugin_audio: enabled controller reset to fix suspend with NVIDIA
  - plugin_irq: fixed expansion of variables
  - plugin_irqbalance: switched to IRQBALANCE_BANNED_CPULIST

* Thu Jun  6 2024 Jaroslav Škarvada <jskarvad@redhat.com> - 2.23.0-1
- new release
  - migrated profiles to /etc/tuned/profiles/ and /usr/lib/tuned/profiles/
  - added an option to configure profile directories
    resolves: RHEL-26157
  - daemon: buffer sighup signal
    resolves: RHEL-31180
  - api: added commands to dynamically create/destroy instances
  - functions: added 'intel_recommended_pstate'
  - functions: added 'log' which helps with debugging
  - plugins: added plugin_irq
  - plugin_net: do not read monitors if dynamic tuning is disabled
    resolves: RHEL-28757
  - plugin_video: added support for amdgpu `panel_power_savings` attribute
  - plugin_cpu: check that writes are necessary if they may cause redundant IPIs
    resolves: RHEL-25613
  - sap-netweaver: increased vm.max_map_count
    resolves: RHEL-31757
  - tuned-ppd: Detect battery change events

* Thu Feb 22 2024 Jaroslav Škarvada <jskarvad@redhat.com> - 2.22.1-1
- new release
  - rebased tuned to latest upstream
    related: RHEL-17121
  - renamed intel_uncore plugin to uncore
  - network-throughput: increased net.ipv4.tcp_rmem default value
    resolves: RHEL-25847

* Fri Feb 16 2024 Jaroslav Škarvada <jskarvad@redhat.com> - 2.22.0-1
- new release
  - rebased tuned to latest upstream
    related: RHEL-17121

* Fri Feb  9 2024 Jaroslav Škarvada <jskarvad@redhat.com> - 2.22.0-0.1.rc1
- new release
  - rebased tuned to latest upstream
    resolves: RHEL-17121
  - print all arguments of failing commands in error messages
    resolves: RHEL-3689
  - plugin_sysctl: added support for sysctl names with slash
    resolves: RHEL-3707
  - tuned-adm: added support for moving devices between plugin instances
    resolves: RHEL-15141
  - api: added methods for retrieval of plugin instances and devices
    resolves: RHEL-15137
  - plugin_cpu: amd-pstate mentioned instead of just intel_pstate
    resolves: RHEL-16469
  - hotplug: do not report ENOENT errors on device remove
    resolves: RHEL-11342
  - plugin_sysctl: expand variables when reporting overrides
    resolves: RHEL-18972
  - plugin_acpi: new plugin which handles ACPI platform_profile
    resolves: RHEL-16966
  - plugin_bootloader: skip calling rpm-ostree kargs in no-op case
    resolves: RHEL-20767
  - plugin_cpu: support cstate settings of pm_qos_resume_latency_us
    resolves: RHEL-21129
  - scheduler: add option for ignoring IRQs affinity
    resolves: RHEL-21923
  - plugin_intel_uncore: new plugin for uncore setting

* Tue Aug 29 2023 Jaroslav Škarvada <jskarvad@redhat.com> - 2.21.0-1
- new release
  - rebased tuned to latest upstream
    related: rhbz#2182117
  - api: fixed stop method not to require any parameter
    resolves: rhbz#2235637

* Sun Aug 20 2023 Jaroslav Škarvada <jskarvad@redhat.com> - 2.21.0-0.1.rc1
- new release
  - rebased tuned to latest upstream
    resolves: rhbz#2182117
  - plugin_scheduler: fix perf fd leaks
    resolves: rhbz#2173938
  - allow skipping rollback when restarting TuneD or switching profile
    resolves: rhbz#2203142
  - function_calc_isolated_cores: no errors for offline CPUs
    resolves: rhbz#2217015
  - sap-hana: new profile sap-hana-kvm-guest
    resolves: rhbz#2173740
  - serialized SIGHUP handler to prevent possible bootcmdline corruption
    resolves: rhbz#2215298

* Fri Feb 17 2023 Jaroslav Škarvada <jskarvad@redhat.com> - 2.20.0-1
- new release
  - rebased tuned to latest upstream
    related: rhbz#2133815
  - fixed possible traceback on SIGHUP
    resolves: rhbz#2169712
  - updated manual pages to be consistent
  - tuned-adm: better error message for unauthorized switch_profile
  - plugin_sysctl: report reapplied sysctls only on different values

* Wed Feb  8 2023 Jaroslav Škarvada <jskarvad@redhat.com> - 2.20.0-0.1.rc1
- new release
  - rebased tuned to latest upstream
    resolves: rhbz#2133815
  - systemd: relax polkit requirement
    resolves: rhbz#2065591
  - sysvinit: fixed path
    resolves: rhbz#2118301
  - plugin_cpu: added support for pm_qos_resume_latency_us
    resolves: rhbz#2118786
  - do not exit on duplicate config lines
    resolves: rhbz#2071418
  - profiles: new cpu-partitioning-powersave profile
  - profiles: new profile for AWS EC2
    resolves: rhbz#1935848
  - API: add support for moving devices between instances
    resolves: rhbz#2113925
  - D-Bus: send tracebacks through D-Bus only in debug mode
    resolves: rhbz#2159680
  - Makefile: added fix for python-3.12
    resolves: rhbz#2154801
  - throughput-performance: set net.core.somaxconn to at least 2048
    resolves: rhbz#1998310
  - plugin_scheduler: do not leak FDs from the perf
    resolves: rhbz#2080227
  - plugin_cpu: added support for intel_pstate scaling driver
    resolves: rhbz#2095829
  - added support for the API access through the Unix Domain Socket
    resolves: rhbz#2113900

* Fri Aug 19 2022 Jaroslav Škarvada <jskarvad@redhat.com> - 2.19.0-1
- new release
  - rebased tuned to latest upstream
    related: rhbz#2057609

* Tue Aug  9 2022 Jaroslav Škarvada <jskarvad@redhat.com> - 2.19.0-0.1.rc1
- new release
  - rebased tuned to latest upstream
    resolves: rhbz#2057609
  - fixed parsing of inline comments
    resolves: rhbz#2060138
  - added support for quotes in isolated_cores specification
    resolves: rhbz#1891036
  - spec: reduced weak dependencies
    resolves: rhbz#2093841
  - recommend: do not ignore syspurpose_role if there is no syspurpose
    resolves: rhbz#2030580
  - added support for initial autosetup of isolated_cores
    resolves: rhbz#2093847

* Wed Feb  9 2022 Jaroslav Škarvada <jskarvad@redhat.com> - 2.18.0-1
- new release
  - rebased tuned to latest upstream
    related: rhbz#2003833
  - tuned-gui: fixed creation of new profile

* Wed Feb  2 2022 Jaroslav Škarvada <jskarvad@redhat.com> - 2.18.0-0.1.rc1
- new release
  - rebased tuned to latest upstream
    resolves: rhbz#2003833
  - profiles: fix improper parsing of include directive
    resolves: rhbz#2017924
  - disk: added support for the nvme
    resolves: rhbz#1854816
  - cpu: extended cstate force_latency syntax to allow skipping zero latency
    resolves: rhbz#2002744
  - net: added support for the txqueuelen
    resolves: rhbz#2015044
  - bootloader: on s390(x) remove TuneD variables from the BLS
    resolves: rhbz#1978786
  - daemon: don't do full rollback on systemd failure
    resolves: rhbz#2011459
  - spec: do not require subscription-manager on CentOS
    resolves: rhbz#2028865

* Sun Jan 16 2022 Jaroslav Škarvada <jskarvad@redhat.com> - 2.17.0-1
- new release
  - rebased tuned to latest upstream
    related: rhbz#2003838

* Sun Jan  2 2022 Jaroslav Škarvada <jskarvad@redhat.com> - 2.17.0-0.1.rc1
- new release
  - rebased tuned to latest upstream
    resolves: rhbz#2003838
  - cpu-partitioning: fixed no_balance_cores on newer kernels
    resolves: rhbz#1874596
  - scheduler: allow exclude of processes from the specific cgroup(s)
    resolves: rhbz#1980715
  - switched to the configparser from the configobj
    resolves: rhbz#1936386
  - spec: do not require subscription-manager on CentOS
    resolves: rhbz#2029405

* Wed Jul 21 2021 Jaroslav Škarvada <jskarvad@redhat.com> - 2.16.0-1
- new release
  - rebased tuned to latest upstream
    related: rhbz#1936426

* Wed Jul  7 2021 Jaroslav Škarvada <jskarvad@redhat.com> - 2.16.0-0.1.rc1
- new release
  - rebased tuned to latest upstream
    resolves: rhbz#1936426
  - realtime: "isolate_managed_irq=Y" should be mentioned in
    "/etc/tuned/realtime-virtual-*-variables.conf"
    resolves: rhbz#1817827
  - realtime: changed tuned default to "isolcpus=domain,managed_irq,X-Y"
    resolves: rhbz#1820626
  - applying a profile with multiple inheritance where parents include a common
    ancestor fails
    resolves: rhbz#1825882
  - failure in moving i40e IRQ threads to housekeeping CPUs from isolated CPUs
    resolves: rhbz#1933069
  - sort network devices before matching by regex
    resolves: rhbz#1939970
  - net: fixed traceback while adjusting the netdev queue count
    resolves: rhbz#1943291
  - net: fixed traceback if the first listed device returns netlink error
    resolves: rhbz#1944686
  - realtime: improve verification
    resolves: rhbz#1947858
  - bootloader: add support for the rpm-ostree
    resolves: rhbz#1950164
  - net: fixed traceback if a device channel contains n/a
    resolves: rhbz#1974071
  - mssql: updated the profile
    resolves: rhbz#1942733
  - realtime: disabled kvm.nx_huge_page kernel module option in
    realtime-virtual-host profile
    resolves: rhbz#1976825
  - realtime: explicitly set 'irqaffinity=~<isolated_cpu_mask>' in kernel
    command line
    resolves: rhbz#1974820
  - scheduler: added abstraction for the sched_* and numa_* variables which
    were previously accessible through the sysctl
    resolves: rhbz#1952687
  - recommend: fixed wrong profile on ppc64le bare metal servers
    resolves: rhbz#1959889

* Thu Dec 17 2020 Jaroslav Škarvada <jskarvad@redhat.com> - 2.15.0-1
- new release
  - rebased tuned to latest upstream
    related: rhbz#1874052

* Tue Dec  1 2020 Jaroslav Škarvada <jskarvad@redhat.com> - 2.15.0-0.1.rc1
- new release
  - rebased tuned to latest upstream
    resolves: rhbz#1874052
  - added plugin service for linux services control
    resolves: rhbz#1869991
  - scheduler: added default_irq_smp_affinity option
    resolves: rhbz#1896348
  - bootloader: skip boom managed BLS snippets
    resolves: rhbz#1901532
  - scheduler: added perf_process_fork option to enable processing of fork
    resolves: rhbz#1894610
  - scheduler: added perf_mmap_pages option to set perf buffer size
    resolves: rhbz#1890219
  - bootloader: fixed cmdline duplication with BLS and grub2-mkconfig
    resolves: rhbz#1777874

* Mon Jun 15 2020 Jaroslav Škarvada <jskarvad@redhat.com> - 2.14.0-1
- new release
  - rebased tuned to latest upstream
    related: rhbz#1792264

* Mon Jun  8 2020 Jaroslav Škarvada <jskarvad@redhat.com> - 2.14.0-0.1.rc1
- new release
  - rebased tuned to latest upstream
    resolves: rhbz#1792264
  - oracle: turned off NUMA balancing
    resolves: rhbz#1782233
  - man: documented the possibility to apply multiple profiles
    resolves: rhbz#1794337
  - cpu-partitioning: disabled kernel.timer_migration
    resolves: rhbz#1797629
  - profiles: new profile optimize-serial-console
    resolves: rhbz#1840689
  - added support for a post-loaded profile
    resolves: rhbz#1798183
  - plugins: new irqbalance plugin
    resolves: rhbz#1784645
  - throughput-performance: added architecture specific tuning for Marvell ThunderX
    resolves: rhbz#1746961
  - throughput-performance: added architecture specific tuning for AMD
    resolves: rhbz#1746957
  - scheduler: added support for cgroups
    resolves: rhbz#1784648

* Wed Dec 11 2019 Jaroslav Škarvada <jskarvad@redhat.com> - 2.13.0-1
- new release
  - rebased tuned to latest upstream
    related: rhbz#1738250
  - sap-hana: updated tuning
    resolves: rhbz#1779821
  - latency-performance: updated tuning
    resolves: rhbz#1779759
  - added sst profile
    resolves: rhbz#1743879

* Sun Dec  1 2019 Jaroslav Škarvada <jskarvad@redhat.com> - 2.13.0-0.1.rc1
- new release
  - rebased tuned to latest upstream
    resolves: rhbz#1738250
  - cpu: fixed checking if EPB is supported
    resolves: rhbz#1690929
  - scheduler: fixed IRQ SMP affinity verification to respect ignore_missing
    resolves: rhbz#1729936
  - realtime: enabled ktimer_lockless_check
    resolves: rhbz#1734096
  - plugins: support cpuinfo_regex and uname_regex matching
    resolves: rhbz#1748965
  - sysctl: made reapply_sysctl ignore configs from /usr
    resolves: rhbz#1759597
  - added support for multiple include directives
    resolves: rhbz#1760390
  - realtime: added nowatchdog kernel command line option
    resolves: rhbz#1767614

* Thu Jun 27 2019 Jaroslav Škarvada <jskarvad@redhat.com> - 2.12.0-1
- new release
  - rebased tuned to latest upstream
    related: rhbz#1685585

* Wed Jun 12 2019 Jaroslav Škarvada <jskarvad@redhat.com> - 2.12.0-0.1.rc1
- new release
  - rebased tuned to latest upstream
    resolves: rhbz#1685585
  - sap-netweaver: changed values of kernel.shmall and kernel.shmmax to RHEL-8 defaults
    resolves: rhbz#1708418
  - sap-netweaver: changed value of kernel.sem to RHEL-8 default
    resolves: rhbz#1701394
  - sap-hana-vmware: dropped profile
    resolves: rhbz#1715541
  - s2kb function: fixed to be compatible with python3
    resolves: rhbz#1684122
  - do fallback to the powersave governor (balanced and powersave profiles)
    resolves: rhbz#1679205
  - added support for negation of CPU list
    resolves: rhbz#1676588
  - switched from sysctl tool to own implementation
    resolves: rhbz#1666678
  - realtime-virtual-host: added tsc-deadline=on to qemu cmdline
    resolves: rhbz#1554458
  - fixed handling of devices that have been removed and re-attached
    resolves: rhbz#1677730

* Thu Mar 21 2019 Jaroslav Škarvada <jskarvad@redhat.com> - 2.11.0-1
- new release
  - rebased tuned to latest upstream
    related: rhbz#1643654
  - used dmidecode only on x86 architectures
    resolves: rhbz#1688371
  - recommend: fixed to work without tuned daemon running
    resolves: rhbz#1687397

* Sun Mar 10 2019 Jaroslav Škarvada <jskarvad@redhat.com> - 2.11.0-0.1.rc1
- new release
  - rebased tuned to latest upstream
    resolves: rhbz#1643654
  - use online CPUs for cpusets calculations instead of present CPUs
    resolves: rhbz#1613478
  - realtime-virtual-guest: run script.sh
    related: rhbz#1616043
  - make python-dmidecode a weak dependency
    resolves: rhbz#1565598
  - make virtual-host identical to latency-performance
    resolves: rhbz#1588932
  - added support for Boot loader specification (BLS)
    resolves: rhbz#1576435
  - scheduler: keep polling file objects alive long enough
    resolves: rhbz#1659140
  - mssql: updated tuning
    resolves: rhbz#1660178
  - s2kb: fixed to be compatible with python3
    resolves: rhbz#1684122
  - profiles: fallback to the 'powersave' scaling governor
    resolves: rhbz#1679205
  - disable KSM only once, re-enable it only on full rollback
    resolves: rhbz#1622239
  - functions: reworked setup_kvm_mod_low_latency to count with kernel changes
    resolves: rhbz#1649408
  - updated virtual-host profile
    resolves: rhbz#1569375
  - added log message for unsupported parameters in plugin_net
    resolves: rhbz#1533852
  - added range feature for cpu exclusion
    resolves: rhbz#1533908
  - make a copy of devices when verifying tuning
    resolves: rhbz#1592743
  - fixed disk plugin/plugout problem
    resolves: rhbz#1595156
  - fixed unit configuration reading
    resolves: rhbz#1613379
  - reload profile configuration on SIGHUP
    resolves: rhbz#1631744
  - use built-in functionality to apply system sysctl
    resolves: rhbz#1663412

* Wed Jul  4 2018 Jaroslav Škarvada <jskarvad@redhat.com> - 2.10.0-1
- new release
  - rebased tuned to latest upstream
    related: rhbz#1546598
  - IRQ affinity handled by scheduler plugin
    resolves: rhbz#1590937

* Mon Jun 11 2018 Jaroslav Škarvada <jskarvad@redhat.com> - 2.10.0-0.1.rc1
- new release
  - rebased tuned to latest upstream
    resolves: rhbz#1546598
  - script: show stderr output in the log
    resolves: rhbz#1536476
  - realtime-virtual-host: script.sh: add error checking
    resolves: rhbz#1461509
  - man: improved tuned-profiles-cpu-partitioning.7
    resolves: rhbz#1548148
  - bootloader: check if grub2_cfg_file_name is None in _remove_grub2_tuning()
    resolves: rhbz#1571403
  - plugin_scheduler: whitelist/blacklist processed also for thread names
    resolves: rhbz#1512295
  - bootloader: patch all GRUB2 config files
    resolves: rhbz#1556990
  - profiles: added mssql profile
    resolves: rhbz#1442122
  - tuned-adm: print log excerpt when changing profile
    resolves: rhbz#1538745
  - cpu-partitioning: use no_balance_cores instead of no_rebalance_cores
    resolves: rhbz#1550573
  - sysctl: support assignment modifiers as other plugins do
    resolves: rhbz#1564092
  - oracle: fixed ip_local_port_range parity warning
    resolves: rhbz#1527219
  - Fix verifying cpumask on systems with more than 32 cores
    resolves: rhbz#1528368
  - oracle: updated the profile to be in sync with KCS 39188
    resolves: rhbz#1447323

* Sun Oct 29 2017 Jaroslav Škarvada <jskarvad@redhat.com> - 2.9.0-1
- new release
  - rebased tuned to latest upstream
    related: rhbz#1467576

* Fri Oct 20 2017 Jaroslav Škarvada <jskarvad@redhat.com> - 2.9.0-0.2.rc2
- new release
  - rebased tuned to latest upstream
    related: rhbz#1467576
  - fixed expansion of the variables in the 'devices' section
    related: rhbz#1490399
  - cpu-partitioning: add no_rebalance_cores= option
    resolves: rhbz#1497182

* Thu Oct 12 2017 Jaroslav Škarvada <jskarvad@redhat.com> - 2.9.0-0.1.rc1
- new release
  - rebased tuned to latest upstream
    resolves: rhbz#1467576
  - added recommend.d functionality
    resolves: rhbz#1459146
  - recommend: added support for matching of processes
    resolves: rhbz#1461838
  - plugin_video: added support for the 'dpm' power method
    resolves: rhbz#1417659
  - list available profiles on 'tuned-adm profile'
    resolves: rhbz#988433
  - cpu-partitioning: used tuned instead of tuna for cores isolation
    resolves: rhbz#1442229
  - inventory: added workaround for pyudev < 0.18
    resolves: rhbz#1251240
  - realtime: used skew_tick=1 in kernel cmdline
    resolves: rhbz#1447938
  - realtime-virtual-guest: re-assigned kernel thread priorities
    resolves: rhbz#1452357
  - bootloader: splitted string for removal from cmdline
    resolves: rhbz#1461279
  - network-latency: added skew_tick=1 kernel command line parameter
    resolves: rhbz#1451073
  - bootloader: accepted only certain values for initrd_remove_dir
    resolves: rhbz#1455161
  - increased udev monitor buffer size, made it configurable
    resolves: rhbz#1442306
  - bootloader: don't add nonexistent overlay image to grub.cfg
    resolves: rhbz#1454340
  - plugin_cpu: don't log error in execute() if EPB is not supported
    resolves: rhbz#1443182
  - sap-hana: fixed description of the sap-hana profiles
    resolves: rhbz#1482005
  - plugin_systemd: on full_rollback notify about need of initrd regeneration
    resolves: rhbz#1469258
  - don't log errors about missing files on verify with ignore_missing set
    resolves: rhbz#1451435
  - plugin_scheduler: improved logging
    resolves: rhbz#1474961
  - improved checking if we are rebooting or not
    resolves: rhbz#1475571
  - started dbus exports after a profile is applied
    resolves: rhbz#1443142
  - sap-hana: changed force_latency to 70
    resolves: rhbz#1501252

* Fri Apr  7 2017 Jaroslav Škarvada <jskarvad@redhat.com> - 2.8.0-1
- new release
  - rebase tuned to latest upstream
    resolves: rhbz#1388454
  - cpu-partitioning: enabled timer migration
    resolves: rhbz#1408308
  - cpu-partitioning: disabled kvmclock sync and ple
    resolves: rhbz#1395855
  - spec: muted error if there is no selinux support
    resolves: rhbz#1404214
  - units: implemented instance priority
    resolves: rhbz#1246172
  - bootloader: added support for initrd overlays
    resolves: rhbz#1414098
  - cpu-partitioning: set CPUAffinity early in initrd image
    resolves: rhbz#1394965
  - cpu-partitioning: set workqueue affinity early
    resolves: rhbz#1395899
  - scsi_host: fixed probing of ALPM, missing ALPM logged as info
    resolves: rhbz#1416712
  - added new profile cpu-partitioning
    resolves: rhbz#1359956
  - bootloader: improved inheritance
    resolves: rhbz#1274464
  - units: mplemented udev-based regexp device matching
    resolves: rhbz#1251240
  - units: introduced pre_script, post_script
    resolves: rhbz#1246176
  - realtime-virtual-host: accommodate new ktimersoftd thread
    resolves: rhbz#1332563
  - defirqaffinity: fixed traceback due to syntax error
    resolves: rhbz#1369791
  - variables: support inheritance of variables
    resolves: rhbz#1433496
  - scheduler: added support for cores isolation
    resolves: rhbz#1403309
  - tuned-profiles-nfv splitted to host/guest and dropped unneeded dependency
    resolves: rhbz#1413111
  - desktop: fixed typo in profile summary
    resolves: rhbz#1421238
  - with systemd don't do full rollback on shutdown / reboot
    resolves: rhbz#1421286
  - builtin functions: added virt_check function and support to include
    resolves: rhbz#1426654
  - cpulist_present: explicitly sorted present CPUs
    resolves: rhbz#1432240
  - plugin_scheduler: fixed initialization
    resolves: rhbz#1433496
  - log errors when applying a profile fails
    resolves: rhbz#1434360
  - systemd: added support for older systemd CPUAffinity syntax
    resolves: rhbz#1441791
  - scheduler: added workarounds for low level exceptions from
    python-linux-procfs
    resolves: rhbz#1441792
  - bootloader: workaround for adding tuned_initrd to new kernels on restart
    resolves: rhbz#1441797

* Tue Aug  2 2016 Jaroslav Škarvada <jskarvad@redhat.com> - 2.7.1-1
- new-release
  - gui: fixed traceback caused by DBus paths copy&paste error
    related: rhbz#1356369
  - tuned-adm: fixed traceback of 'tuned-adm list' if daemon is not running
    resolves: rhbz#1358857
  - tuned-adm: fixed profile_info traceback
    resolves: rhbz#1362481

* Tue Jul 19 2016 Jaroslav Škarvada <jskarvad@redhat.com> - 2.7.0-1
- new-release
  - gui: fixed save profile
    resolves: rhbz#1242491
  - tuned-adm: added --ignore-missing parameter
    resolves: rhbz#1243807
  - plugin_vm: added transparent_hugepage alias
    resolves: rhbz#1249610
  - plugins: added modules plugin
    resolves: rhbz#1249618
  - plugin_cpu: do not show error if cpupower or x86_energy_perf_policy are
    missing
    resolves: rhbz#1254417
  - tuned-adm: fixed restart attempt if tuned is not running
    resolves: rhbz#1258755
  - nfv: avoided race condition by using synchronous mode
    resolves: rhbz#1259039
  - realtime: added check for isolcpus sanity
    resolves: rhbz#1264128
  - pm_qos: fixed exception if PM_QoS is not available
    resolves: rhbz#1296137
  - plugin_sysctl: reapply system sysctl after Tuned sysctl are applied
    resolves: rhbz#1302953
  - atomic: increase number of inotify watches
    resolves: rhbz#1322001
  - realtime-virtual-host/guest: added rcu_nocbs kernel boot parameter
    resolves: rhbz#1334479
  - realtime: fixed kernel.sched_rt_runtime_us to be -1
    resolves: rhbz#1346715
  - tuned-adm: fixed detection of no_daemon mode
    resolves: rhbz#1351536
  - plugin_base: correctly strip assignment modifiers even if not used
    resolves: rhbz#1353142
  - plugin_disk: try to workaround embedded '/' in device names
    related: rhbz#1353142
  - sap-hana: explicitly setting kernel.numa_balancing = 0 for better performance
    resolves: rhbz#1355768
  - switched to polkit authorization
    resolves: rhbz#1095142
  - plugins: added scsi_host plugin
    resolves: rhbz#1246992
  - spec: fixed conditional support for grub2 to work with selinux
    resolves: rhbz#1351937
  - gui: added tuned icon and desktop file
    resolves: rhbz#1356369

* Tue Jan  5 2016 Jaroslav Škarvada <jskarvad@redhat.com> - 2.6.0-1
- new-release
  - plugin_cpu: do not show error if cpupower or x86_energy_perf_policy are missing
  - plugin_sysctl: fixed quoting of sysctl values
    resolves: rhbz#1254538
  - tuned-adm: added log file location hint to verify command output
  - libexec: fixed listdir and isdir in defirqaffinity.py
    resolves: rhbz#1252160
  - plugin_cpu: save and restore only intel pstate attributes that were changed
    resolves: rhbz#1252156
  - functions: fixed sysfs save to work with options
    resolves: rhbz#1251507
  - plugins: added scsi_host plugin
  - tuned-adm: fixed restart attempt if tuned is not running
  - spec: fixed post scriptlet to work without grub
    resolves: rhbz#1265654
  - tuned-profiles-nfv: fix find-lapictscdeadline-optimal.sh for CPUS where ns > 6500
    resolves: rhbz#1267284
  - functions: fixed restore_logs_syncing to preserve SELinux context on rsyslog.conf
    resolves: rhbz#1268901
  - realtime: set unboud workqueues cpumask
    resolves: rhbz#1259043
  - spec: correctly remove tuned footprint from /etc/default/grub
    resolves: rhbz#1268845
  - gui: fixed creation of new profile
    resolves: rhbz#1274609
  - profiles: removed nohz_full from the realtime profile
    resolves: rhbz#1274486
  - profiles: Added nohz_full and nohz=on to realtime guest/host profiles
    resolves: rhbz#1274445
  - profiles: fixed lapic_timer_adv_ns cache
    resolves: rhbz#1259452
  - plugin_sysctl: pass verification even if the option doesn't exist
    related: rhbz#1252153
  - added support for 'summary' and 'description' of profiles,
    extended D-Bus API for Cockpit
    related: rhbz#1228356

* Tue Aug  4 2015 Jaroslav Škarvada <jskarvad@redhat.com> - 2.5.1-1
- new-release
  related: rhbz#1155052
  - plugin_scheduler: work with nohz_full
    resolves: rhbz#1247184
  - fixed realtime-virtual-guest/host profiles packaged twice
    resolves: rhbz#1249028
  - fixed requirements of realtime and nfv profiles
  - fixed tuned-gui not starting
  - various other minor fixes

* Sun Jul  5 2015 Jaroslav Škarvada <jskarvad@redhat.com> - 2.5.0-1
- new-release
  resolves: rhbz#1155052
  - add support for ethtool -C to tuned network plugin
    resolves: rhbz#1152539
  - add support for ethtool -K to tuned network plugin
    resolves: rhbz#1152541
  - add support for calculation of values for the kernel command line
    resolves: rhbz#1191595
  - no error output if there is no hdparm installed
    resolves: rhbz#1191775
  - do not run hdparm on hotplug events if there is no hdparm tuning
    resolves: rhbz#1193682
  - add oracle tuned profile
    resolves: rhbz#1196298
  - fix bash completions for tuned-adm
    resolves: rhbz#1207668
  - add glob support to tuned sysfs plugin
    resolves: rhbz#1212831
  - add tuned-adm verify subcommand
    resolves: rhbz#1212836
  - do not install tuned kernel command line to rescue kernels
    resolves: rhbz#1223864
  - add variables support
    resolves: rhbz#1225124
  - add built-in support for unit conversion into tuned
    resolves: rhbz#1225135
  - fix vm.max_map_count setting in sap-netweaver profile
    resolves: rhbz#1228562
  - add tuned profile for RHEL-RT
    resolves: rhbz#1228801
  - plugin_scheduler: added support for runtime tuning of processes
    resolves: rhbz#1148546
  - add support for changing elevators on xvd* devices (Amazon EC2)
    resolves: rhbz#1170152
  - add workaround to be run after systemd-sysctl
    resolves: rhbz#1189263
  - do not change settings of transparent hugepages if set in kernel cmdline
    resolves: rhbz#1189868
  - add tuned profiles for RHEL-NFV
    resolves: rhbz#1228803
  - plugin_bootloader: apply $tuned_params to existing kernels
    resolves: rhbz#1233004

* Thu Oct 16 2014 Jaroslav Škarvada <jskarvad@redhat.com> - 2.4.1-1
- new-release
  - fixed return code of tuned grub template
    resolves: rhbz#1151768
  - plugin_bootloader: fix for multiple parameters on command line
    related: rhbz#1148711
  - tuned-adm: fixed traceback on "tuned-adm list"
    resolves: rhbz#1149162
  - plugin_bootloader is automatically disabled if grub2 is not found
    resolves: rhbz#1150047
  - plugin_disk: set_spindown and set_APM made independent
    resolves: rhbz#976725

* Wed Oct  1 2014 Jaroslav Škarvada <jskarvad@redhat.com> - 2.4.0-1
- new-release
  resolves: rhbz#1093883
  - fixed traceback if profile cannot be loaded
    related: rhbz#953128
  - powertop2tuned: fixed traceback if rewriting file instead of dir
    resolves: rhbz#963441
  - daemon: fixed race condition in start/stop
  - improved timings, it can be fine tuned in /etc/tuned/tuned-main.conf
    resolves: rhbz#1028122
  - throughput-performance: altered dirty ratios for better performance
    resolves: rhbz#1043533
  - latency-performance: leaving THP on its default
    resolves: rhbz#1064510
  - used throughput-performance profile on server by default
    resolves: rhbz#1063481
  - network-latency: added new profile
    resolves: rhbz#1052418
  - network-throughput: added new profile
    resolves: rhbz#1052421
  - recommend.conf: fixed config file
    resolves: rhbz#1069123
  - spec: added kernel-tools requirement
    resolves: rhbz#1073008
  - systemd: added cpupower.service conflict
    resolves: rhbz#1073392
  - balanced: used medium_power ALPM policy
  - added support for >, < assignment modifiers in tuned.conf
  - handled root block devices
  - balanced: used conservative CPU governor
    resolves: rhbz#1124125
  - plugins: added selinux plugin
  - plugin_net: added nf_conntrack_hashsize parameter
  - profiles: added atomic-host profile
    resolves: rhbz#1091977
  - profiles: added atomic-guest profile
    resolves: rhbz#1091979
  - moved profile autodetection from post install script to tuned daemon
    resolves: rhbz#1144067
  - profiles: included sap-hana and sap-hana-vmware profiles
  - man: structured profiles manual pages according to sub-packages
  - added missing hdparm dependency
    resolves: rhbz#1144858
  - improved error handling of switch_profile
    resolves: rhbz#1068699
  - tuned-adm: active: detect whether tuned daemon is running
    related: rhbz#1068699
  - removed active_profile from RPM verification
    resolves: rhbz#1104126
  - plugin_disk: readahead value can be now specified in sectors
    resolves: rhbz#1127127
  - plugins: added bootloader plugin
    resolves: rhbz#1044111
  - plugin_disk: added error counter to hdparm calls
  - plugins: added scheduler plugin
    resolves: rhbz#1100826
  - added tuned-gui

* Wed Nov  6 2013 Jaroslav Škarvada <jskarvad@redhat.com> - 2.3.0-1
- new-release
  resolves: rhbz#1020743
  - audio plugin: fixed audio settings in standard profiles
    resolves: rhbz#1019805
  - video plugin: fixed tunings
  - daemon: fixed crash if preset profile is not available
    resolves: rhbz#953128
  - man: various updates and corrections
  - functions: fixed usb and bluetooth handling
  - tuned: switched to lightweighted pygobject3-base
  - daemon: added global config for dynamic_tuning
    resolves: rhbz#1006427
  - utils: added pmqos-static script for debug purposes
    resolves: rhbz#1015676
  - throughput-performance: various fixes
    resolves: rhbz#987570
  - tuned: added global option update_interval
  - plugin_cpu: added support for x86_energy_perf_policy
    resolves: rhbz#1015675
  - dbus: fixed KeyboardInterrupt handling
  - plugin_cpu: added support for intel_pstate
    resolves: rhbz#996722
  - profiles: various fixes
    resolves: rhbz#922068
  - profiles: added desktop profile
    resolves: rhbz#996723
  - tuned-adm: implemented non DBus fallback control
  - profiles: added sap profile
  - tuned: lowered CPU usage due to python bug
    resolves: rhbz#917587

* Tue Mar 19 2013 Jaroslav Škarvada <jskarvad@redhat.com> - 2.2.2-1
- new-release:
  - cpu plugin: fixed cpupower workaround
  - cpu plugin: fixed crash if cpupower is installed

* Fri Mar  1 2013 Jaroslav Škarvada <jskarvad@redhat.com> - 2.2.1-1
- new release:
  - audio plugin: fixed error handling in _get_timeout
  - removed cpupower dependency, added sysfs fallback
  - powertop2tuned: fixed parser crash on binary garbage
    resolves: rhbz#914933
  - cpu plugin: dropped multicore_powersave as kernel upstream already did
  - plugins: options manipulated by dynamic tuning are now correctly saved and restored
  - powertop2tuned: added alias -e for --enable option
  - powertop2tuned: new option -m, --merge-profile to select profile to merge
  - prefer transparent_hugepage over redhat_transparent_hugepage
  - recommend: use recommend.conf not autodetect.conf
  - tuned.service: switched to dbus type service
    resolves: rhbz#911445
  - tuned: new option --pid, -P to write PID file
  - tuned, tuned-adm: added new option --version, -v to show version
  - disk plugin: use APM value 254 for cleanup / APM disable instead of 255
    resolves: rhbz#905195
  - tuned: new option --log, -l to select log file
  - powertop2tuned: avoid circular deps in include (one level check only)
  - powertop2tuned: do not crash if powertop is not installed
  - net plugin: added support for wake_on_lan static tuning
    resolves: rhbz#885504
  - loader: fixed error handling
  - spec: used systemd-rpm macros
    resolves: rhbz#850347

* Mon Jan 28 2013 Jan Vcelak <jvcelak@redhat.com> 2.2.0-1
- new release:
  - remove nobarrier from virtual-guest (data loss prevention)
  - devices enumeration via udev, instead of manual retrieval
  - support for dynamically inserted devices (currently disk plugin)
  - dropped rfkill plugins (bluetooth and wifi), the code didn't work

* Wed Jan  2 2013 Jaroslav Škarvada <jskarvad@redhat.com> - 2.1.2-1
- new release:
  - systemtap {disk,net}devstat: fix typo in usage
  - switched to configobj parser
  - latency-performance: disabled THP
  - fixed fd leaks on subprocesses

* Thu Dec 06 2012 Jan Vcelak <jvcelak@redhat.com> 2.1.1-1
- fix: powertop2tuned execution
- fix: ownership of /etc/tuned

* Mon Dec 03 2012 Jan Vcelak <jvcelak@redhat.com> 2.1.0-1
- new release:
  - daemon: allow running without selected profile
  - daemon: fix profile merging, allow only safe characters in profile names
  - daemon: implement missing methods in DBus interface
  - daemon: implement profile recommendation
  - daemon: improve daemonization, PID file handling
  - daemon: improved device matching in profiles, negation possible
  - daemon: various internal improvements
  - executables: check for EUID instead of UID
  - executables: run python with -Es to increase security
  - plugins: cpu - fix cpupower execution
  - plugins: disk - fix option setting
  - plugins: mounts - new, currently supports only barriers control
  - plugins: sysctl - fix a bug preventing settings application
  - powertop2tuned: speedup, fix crashes with non-C locales
  - powertop2tuned: support for powertop 2.2 output
  - profiles: progress on replacing scripts with plugins
  - tuned-adm: bash completion - suggest profiles from all supported locations
  - tuned-adm: complete switch to D-bus
  - tuned-adm: full control to users with physical access

* Mon Oct 08 2012 Jaroslav Škarvada <jskarvad@redhat.com> - 2.0.2-1
- New version
- Systemtap scripts moved to utils-systemtap subpackage

* Sun Jul 22 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.0.1-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Tue Jun 12 2012 Jaroslav Škarvada <jskarvad@redhat.com> - 2.0.1-3
- another powertop-2.0 compatibility fix
  Resolves: rhbz#830415

* Tue Jun 12 2012 Jan Kaluza <jkaluza@redhat.com> - 2.0.1-2
- fixed powertop2tuned compatibility with powertop-2.0

* Tue Apr 03 2012 Jaroslav Škarvada <jskarvad@redhat.com> - 2.0.1-1
- new version

* Fri Mar 30 2012 Jan Vcelak <jvcelak@redhat.com> 2.0-1
- first stable release
