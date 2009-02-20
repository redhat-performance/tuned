NAME=tuned
VERSION=$(shell awk '/^Version:/ {print $$2}' tuned.spec)
RELEASE=$(shell awk '/^Release:/ {print $$2}' tuned.spec)
VERSIONED_NAME=$(NAME)-$(VERSION)

DESTDIR=/
MANDIR=/usr/share/man/
GITTAG = r$(subst .,-,$(VERSION))

DIRS = doc contrib tuningplugins monitorplugins
FILES = tuned
DOCS = AUTHORS ChangeLog COPYING INSTALL NEWS README tuned.spec

archive:
	rm -rf $(VERSIONED_NAME)
	mkdir -p $(VERSIONED_NAME)
	cp $(FILES) $(VERSIONED_NAME)/
	cp $(DOCS) $(VERSIONED_NAME)/

	tar cjf $(VERSIONED_NAME).tar.bz2 $(VERSIONED_NAME)
	ln -fs $(VERSIONED_NAME).tar.bz2 latest-archive

tag:
	git tag $(GITTAG)

srpm: archive
	rm -rf rpm-build-dir
	mkdir rpm-build-dir
	rpmbuild --define "_sourcedir `pwd`/rpm-build-dir" --define "_srcrpmdir `pwd`/rpm-build-dir" \
		--define "_specdir `pwd`/rpm-build-dir" --nodeps -ts $(VERSIONED_NAME).tar.bz2
	rm -rf rpm-build-dir

build: 
	# Make Magicfilter

install:
	mkdir -p $(DESTDIR)

	# Install the binaries
	mkdir -p $(DESTDIR)/usr/bin/

	mkdir -p $(DESTDIR)/etc/alchemist/namespace/printconf
	install -m 0644 adl_files/rpm.adl adl_files/local.adl $(DESTDIR)/etc/alchemist/namespace/printconf/

	# drop in some basics
	install -m 0644 printcap.local $(DESTDIR)/etc/

clean:
	rm -rf *.pyc monitorplugins/*.pyc tuningplugins/*.pyc

.PHONY: clean archive srpm tag

