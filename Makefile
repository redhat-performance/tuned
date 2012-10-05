NAME = tuned
VERSION = $(shell awk '/^Version:/ {print $$2}' tuned.spec)
RELEASE = $(shell awk '/^Release:/ {print $$2}' tuned.spec)
UNITDIR = $(shell rpm --eval '%{_unitdir}')
VERSIONED_NAME = $(NAME)-$(VERSION)

DESTDIR = /
PYTHON_SITELIB = /usr/lib/python2.7/site-packages
TUNED_PROFILESDIR = /usr/lib/tuned

archive: clean
	mkdir -p $(VERSIONED_NAME)

	cp AUTHORS COPYING INSTALL README $(VERSIONED_NAME)

	cp tuned.py tuned.spec tuned.service tuned.tmpfiles Makefile tuned-adm.py tuned.bash dbus.conf $(VERSIONED_NAME)
	cp -a doc experiments man profiles systemtap tuned $(VERSIONED_NAME)

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
	echo -n balanced > $(DESTDIR)/etc/tuned/active_profile

	# profiles
	mkdir -p $(DESTDIR)$(TUNED_PROFILESDIR)
	cp -a profiles/* $(DESTDIR)$(TUNED_PROFILESDIR)/

	# Install bash completion
	mkdir -p $(DESTDIR)/etc/bash_completion.d
	install -m 0644 tuned.bash $(DESTDIR)/etc/bash_completion.d/tuned.bash

	# log dir
	mkdir -p $(DESTDIR)/var/log/tuned

	# runtime directory
	mkdir -p $(DESTDIR)/run/tuned
	mkdir -p $(DESTDIR)/etc/tmpfiles.d
	install -m 0644 tuned.tmpfiles $(DESTDIR)/etc/tmpfiles.d/tuned.conf

	# systemd units
	mkdir -p $(DESTDIR)$(UNITDIR)
	install -m 0644 tuned.service $(DESTDIR)$(UNITDIR)/tuned.service

	# dbus configuration
	mkdir -p $(DESTDIR)/etc/dbus-1/system.d
	install -m 0644 dbus.conf $(DESTDIR)/etc/dbus-1/system.d/com.redhat.tuned.conf

	# manual pages *.8
	mkdir -p $(DESTDIR)/usr/share/man/man8
	for file in man/*.8; do \
		install -m 0644 $$file $(DESTDIR)/usr/share/man/man8; \
	done

	# manual pages *.5
	mkdir -p $(DESTDIR)/usr/share/man/man5
	for file in man/*.5; do \
		install -m 0644 $$file $(DESTDIR)/usr/share/man/man5; \
	done

	# documentation
	mkdir -p $(DESTDIR)/usr/share/doc/$(VERSIONED_NAME)
	cp -a doc/* $(DESTDIR)/usr/share/doc/$(VERSIONED_NAME)
	cp AUTHORS COPYING README $(DESTDIR)/usr/share/doc/$(VERSIONED_NAME)

clean:
	find -name "*.pyc" | xargs rm -f
	rm -rf $(VERSIONED_NAME) rpm-build-dir

test:
	python -m unittest discover tests

.PHONY: clean archive srpm tag test

