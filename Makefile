NAME = tuned
# set to devel for nightly GIT snapshot
BUILD = release
# which config to use in mock-build target
MOCK_CONFIG = rhel-7-x86_64
VERSION = $(shell awk '/^Version:/ {print $$2}' tuned.spec)
ifeq ($(BUILD), release)
	RPM_ARGS += --without snapshot
	MOCK_ARGS += --without=snapshot
	RPM_VERSION = $(NAME)-$(VERSION)-1
else
	RPM_ARGS += --with snapshot
	MOCK_ARGS += --with=snapshot
	GIT_SHORT_COMMIT = $(shell git rev-parse --short=8 --verify HEAD)
	GIT_DATE = $(shell date +'%Y%m%d')
	GIT_SUFFIX = $(GIT_DATE)git$(GIT_SHORT_COMMIT)
	GIT_PSUFFIX = .$(GIT_SUFFIX)
	RPM_VERSION = $(NAME)-$(VERSION)-1$(GIT_PSUFFIX)
endif
UNITDIR = $(shell rpm --eval '%{_unitdir}' 2>/dev/null || echo /usr/lib/systemd/system)
TMPFILESDIR = $(shell rpm --eval '%{_tmpfilesdir}' 2>/dev/null || echo /usr/lib/tmpfiles.d)
VERSIONED_NAME = $(NAME)-$(VERSION)$(GIT_PSUFFIX)

DOCDIR = /usr/share/doc/$(NAME)
PYTHON_SITELIB = $(shell python -c 'from distutils.sysconfig import get_python_lib; print get_python_lib();' || echo /usr/lib/python2.7/site-packages)
TUNED_PROFILESDIR = /usr/lib/tuned
BASH_COMPLETIONS = /usr/share/bash-completion/completions

release-dir:
	mkdir -p $(VERSIONED_NAME)

release-cp: release-dir
	cp -a AUTHORS COPYING INSTALL README $(VERSIONED_NAME)

	cp -a tuned.py tuned.spec tuned.service tuned.tmpfiles Makefile tuned-adm.py \
		tuned-adm.bash dbus.conf recommend.conf tuned-main.conf 00_tuned \
		bootcmdline org.tuned.gui.policy tuned-gui.py tuned-gui.glade \
		$(VERSIONED_NAME)
	cp -a doc experiments libexec man profiles systemtap tuned contrib $(VERSIONED_NAME)

archive: clean release-cp
	tar cjf $(VERSIONED_NAME).tar.bz2 $(VERSIONED_NAME)

rpm-build-dir:
	mkdir rpm-build-dir

srpm: archive rpm-build-dir
	rpmbuild --define "_sourcedir `pwd`/rpm-build-dir" --define "_srcrpmdir `pwd`/rpm-build-dir" \
		--define "_specdir `pwd`/rpm-build-dir" --nodeps $(RPM_ARGS) -ts $(VERSIONED_NAME).tar.bz2

rpm: archive rpm-build-dir
	rpmbuild --define "_sourcedir `pwd`/rpm-build-dir" --define "_srcrpmdir `pwd`/rpm-build-dir" \
		--define "_specdir `pwd`/rpm-build-dir" --nodeps $(RPM_ARGS) -tb $(VERSIONED_NAME).tar.bz2

clean-mock-result-dir:
	rm -f mock-result-dir/*

mock-result-dir:
	mkdir mock-result-dir

mock-build: srpm
	mock -r $(MOCK_CONFIG) $(MOCK_ARGS) --resultdir=`pwd`/mock-result-dir `ls rpm-build-dir/*$(RPM_VERSION).*.src.rpm | head -n 1`&& \
	rm -f mock-result-dir/*.log

mock-devel-build: srpm
	mock -r $(MOCK_CONFIG) --with=snapshot --resultdir=`pwd`/mock-result-dir `ls rpm-build-dir/*$(RPM_VERSION).*.src.rpm | head -n 1`&& \
	rm -f mock-result-dir/*.log

createrepo: mock-devel-build
	createrepo mock-result-dir

nightly: createrepo
	scp `mock-result-dir/*` jskarvad@fedorapeople.org:/home/fedora/jskarvad/public_html/tuned/devel/repo/

install-dirs:
	mkdir -p $(DESTDIR)$(PYTHON_SITELIB)
	mkdir -p $(DESTDIR)$(TUNED_PROFILESDIR)
	mkdir -p $(DESTDIR)/var/log/tuned
	mkdir -p $(DESTDIR)/run/tuned
	mkdir -p $(DESTDIR)$(DOCDIR)

install: install-dirs
	# library
	cp -a tuned $(DESTDIR)$(PYTHON_SITELIB)

	# binaries
	install -Dpm 0755 tuned.py $(DESTDIR)/usr/sbin/tuned
	install -Dpm 0755 tuned-adm.py $(DESTDIR)/usr/sbin/tuned-adm
	install -Dpm 0755 tuned-gui.py $(DESTDIR)/usr/sbin/tuned-gui
	$(foreach file, $(wildcard systemtap/*), \
		install -Dpm 0755 $(file) $(DESTDIR)/usr/sbin/$(notdir $(file));)

	# glade
	install -Dpm 0755 tuned-gui.glade $(DESTDIR)/usr/share/tuned/ui/tuned-gui.glade

	# tools
	install -Dpm 0755 experiments/powertop2tuned.py $(DESTDIR)/usr/bin/powertop2tuned

	# configuration files
	install -Dpm 0644 tuned-main.conf $(DESTDIR)/etc/tuned/tuned-main.conf
	# None profile in the moment, autodetection will be used
	echo -n > $(DESTDIR)/etc/tuned/active_profile
	install -Dpm 0644 bootcmdline $(DESTDIR)/etc/tuned/bootcmdline

	# profiles & system config
	cp -a profiles/* $(DESTDIR)$(TUNED_PROFILESDIR)/
	install -pm 0644 recommend.conf $(DESTDIR)$(TUNED_PROFILESDIR)/recommend.conf

	# bash completion
	install -Dpm 0644 tuned-adm.bash $(DESTDIR)$(BASH_COMPLETIONS)/tuned-adm

	# runtime directory
	install -Dpm 0644 tuned.tmpfiles $(DESTDIR)$(TMPFILESDIR)/tuned.conf

	# systemd units
	install -Dpm 0644 tuned.service $(DESTDIR)$(UNITDIR)/tuned.service

	# dbus configuration
	install -Dpm 0644 dbus.conf $(DESTDIR)/etc/dbus-1/system.d/com.redhat.tuned.conf

	# grub template
	install -Dpm 0755 00_tuned $(DESTDIR)/etc/grub.d/00_tuned

	# polkit configuration
	install -Dpm 0644 org.tuned.gui.policy $(DESTDIR)/usr/share/polkit-1/actions/org.tuned.gui.policy

	# manual pages
	$(foreach man_section, 5 7 8, $(foreach file, $(wildcard man/*.$(man_section)), \
		install -Dpm 0644 $(file) $(DESTDIR)/usr/share/man/man$(man_section)/$(notdir $(file));))

	# documentation
	cp -a doc/* $(DESTDIR)$(DOCDIR)
	cp AUTHORS COPYING README $(DESTDIR)$(DOCDIR)

	# Install libexec scripts
	$(foreach file, $(wildcard libexec/*), \
		install -Dpm 0755 $(file) $(DESTDIR)/usr/libexec/tuned/$(notdir $(file));)

clean:
	find -name "*.pyc" | xargs rm -f
	rm -rf $(VERSIONED_NAME) rpm-build-dir

test:
	python -m unittest discover tests

.PHONY: clean archive srpm tag test
