NAME = tuned
VERSION = $(shell awk '/^Version:/ {print $$2}' tuned.spec)
RELEASE = $(shell awk '/^Release:/ {print $$2}' tuned.spec)
UNITDIR = $(shell rpm --eval '%{_unitdir}' 2>/dev/null || echo /usr/lib/systemd/system)
TMPFILESDIR = $(shell rpm --eval '%{_tmpfilesdir}' 2>/dev/null || echo /usr/lib/tmpfiles.d)
VERSIONED_NAME = $(NAME)-$(VERSION)

DESTDIR = /
PYTHON_SITELIB = /usr/lib/python2.7/site-packages
TUNED_PROFILESDIR = /usr/lib/tuned
BASH_COMPLETIONS = /usr/share/bash-completion/completions/

archive: clean
	mkdir -p $(VERSIONED_NAME)

	cp AUTHORS COPYING INSTALL README $(VERSIONED_NAME)

	cp tuned.py tuned.spec tuned.service tuned.tmpfiles Makefile tuned-adm.py \
		tuned.bash dbus.conf recommend.conf tuned-main.conf $(VERSIONED_NAME)
	cp -a doc experiments libexec man profiles systemtap tuned $(VERSIONED_NAME)

	tar cjf $(VERSIONED_NAME).tar.bz2 $(VERSIONED_NAME)

srpm: archive
	mkdir rpm-build-dir
	rpmbuild --define "_sourcedir `pwd`/rpm-build-dir" --define "_srcrpmdir `pwd`/rpm-build-dir" \
		--define "_specdir `pwd`/rpm-build-dir" --nodeps -ts $(VERSIONED_NAME).tar.bz2

build:
	# nothing to build

install:
	mkdir -p $(DESTDIR)

	# library
	mkdir -p $(DESTDIR)$(PYTHON_SITELIB)
	cp -a tuned $(DESTDIR)$(PYTHON_SITELIB)

	# binaries
	mkdir -p $(DESTDIR)/usr/sbin
	install -m 0755 tuned.py $(DESTDIR)/usr/sbin/tuned
	install -m 0755 tuned-adm.py $(DESTDIR)/usr/sbin/tuned-adm
	for file in systemtap/*; do \
		install -m 0755 $$file $(DESTDIR)/usr/sbin/; \
	done

	# tools
	mkdir -p $(DESTDIR)/usr/bin
	install -m 0755 experiments/powertop2tuned.py $(DESTDIR)/usr/bin/powertop2tuned

	# configuration files
	mkdir -p $(DESTDIR)/etc/tuned
	install -m 0644 tuned-main.conf $(DESTDIR)/etc/tuned/tuned-main.conf
	# None profile in the moment, autodetection will be used
	echo -n > $(DESTDIR)/etc/tuned/active_profile
	install -m 0644 bootcmdline $(DESTDIR)/etc/tuned/bootcmdline

	# profiles & system config
	mkdir -p $(DESTDIR)$(TUNED_PROFILESDIR)
	cp -a profiles/* $(DESTDIR)$(TUNED_PROFILESDIR)/
	install -m 0644 recommend.conf $(DESTDIR)$(TUNED_PROFILESDIR)/recommend.conf

	# Install bash completion
	mkdir -p $(DESTDIR)$(BASH_COMPLETIONS)
	install -m 0644 tuned.bash $(DESTDIR)$(BASH_COMPLETIONS)/tuned

	# log dir
	mkdir -p $(DESTDIR)/var/log/tuned

	# runtime directory
	mkdir -p $(DESTDIR)/run/tuned
	mkdir -p $(DESTDIR)$(TMPFILESDIR)
	install -m 0644 tuned.tmpfiles $(DESTDIR)$(TMPFILESDIR)/tuned.conf

	# systemd units
	mkdir -p $(DESTDIR)$(UNITDIR)
	install -m 0644 tuned.service $(DESTDIR)$(UNITDIR)/tuned.service

	# dbus configuration
	mkdir -p $(DESTDIR)/etc/dbus-1/system.d
	install -m 0644 dbus.conf $(DESTDIR)/etc/dbus-1/system.d/com.redhat.tuned.conf

	# grub template
	mkdir -p $(DESTDIR)/etc/grub.d
	install -m 0755 00_tuned $(DESTDIR)/etc/grub.d/00_tuned

	# manual pages
	for man_section in 5 7 8; do \
		mkdir -p $(DESTDIR)/usr/share/man/man$$man_section; \
		for file in man/*.$$man_section; do \
			install -m 0644 $$file $(DESTDIR)/usr/share/man/man$$man_section; \
		done; \
	done

	# documentation
	mkdir -p $(DESTDIR)/usr/share/doc/$(NAME)
	cp -a doc/* $(DESTDIR)/usr/share/doc/$(NAME)
	cp AUTHORS COPYING README $(DESTDIR)/usr/share/doc/$(NAME)

	# Install libexec scripts
	install -m 0755 -Dd $(DESTDIR)/usr/libexec/tuned
	for file in libexec/*; do \
		install -m 0755 $$file $(DESTDIR)/usr/libexec/tuned; \
	done

clean:
	find -name "*.pyc" | xargs rm -f
	rm -rf $(VERSIONED_NAME) rpm-build-dir

test:
	python -m unittest discover tests

.PHONY: clean archive srpm tag test

