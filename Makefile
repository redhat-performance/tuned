NAME = tuned
VERSION = $(shell awk '/^Version:/ {print $$2}' tuned.spec)
RELEASE = $(shell awk '/^Release:/ {print $$2}' tuned.spec)
VERSIONED_NAME = $(NAME)-$(VERSION)

DESTDIR = /
MANDIR = /usr/share/man/
GITTAG = r$(subst .,-,$(VERSION))

DIRS = doc contrib tuningplugins monitorplugins
FILES = tuned tuned.spec Makefile tuned.py tuned.initscript tuned.conf
FILES_doc = doc/README.txt doc/TIPS.txt
FILES_contrib = contrib/diskdevstat contrib/netdevstat
FILES_tuningplugins = tuningplugins/disk.py tuningplugins/net.py tuningplugins/__init__.py
FILES_monitorplugins = monitorplugins/disk.py monitorplugins/net.py monitorplugins/__init__.py
DOCS = AUTHORS ChangeLog COPYING INSTALL NEWS README

archive:
	rm -rf $(VERSIONED_NAME)
	mkdir -p $(VERSIONED_NAME)
	cp $(FILES) $(VERSIONED_NAME)/
	cp $(DOCS) $(VERSIONED_NAME)/
	for dir in $(DIRS); do \
                mkdir -p $(VERSIONED_NAME)/$$dir; \
        done;
	cp $(FILES_doc) $(VERSIONED_NAME)/doc
	cp $(FILES_contrib) $(VERSIONED_NAME)/contrib
	cp $(FILES_tuningplugins) $(VERSIONED_NAME)/tuningplugins
	cp $(FILES_monitorplugins) $(VERSIONED_NAME)/monitorplugins

	tar cjf $(VERSIONED_NAME).tar.bz2 $(VERSIONED_NAME)
	ln -fs $(VERSIONED_NAME).tar.bz2 latest-archive

tag:
	git tag $(GITTAG)

srpm: archive
	rm -rf rpm-build-dir
	mkdir rpm-build-dir
	rpmbuild --define "_sourcedir `pwd`/rpm-build-dir" --define "_srcrpmdir `pwd`/rpm-build-dir" \
		--define "_specdir `pwd`/rpm-build-dir" --nodeps -ts $(VERSIONED_NAME).tar.bz2

build: 
	# Nothing to build

install:
	mkdir -p $(DESTDIR)

	# Install the binaries
	mkdir -p $(DESTDIR)/usr/sbin/
	install -m 0755 tuned $(DESTDIR)/usr/sbin/

	# Install the plugins and classes
	mkdir -p $(DESTDIR)/usr/share/$(NAME)/
	mkdir -p $(DESTDIR)/usr/share/$(NAME)/tuningplugins
	mkdir -p $(DESTDIR)/usr/share/$(NAME)/monitorplugins
	install -m 0644 tuned.py $(DESTDIR)/usr/share/$(NAME)/
	for file in $(FILES_tuningplugins); do \
		install -m 0644 $$file $(DESTDIR)/usr/share/$(NAME)/tuningplugins; \
	done
	for file in $(FILES_monitorplugins); do \
		install -m 0644 $$file $(DESTDIR)/usr/share/$(NAME)/monitorplugins; \
	done

	# Install contrib systemtap scripts
	for file in $(FILES_contrib); do \
		install -m 0755 $$file $(DESTDIR)/usr/sbin/; \
	done

	# Install config file
	mkdir -p $(DESTDIR)/etc
	install -m 0644 tuned.conf $(DESTDIR)/etc

	# Install initscript
	mkdir -p $(DESTDIR)/etc/rc.d/init.d
	install -m 0755 tuned.initscript $(DESTDIR)/etc/rc.d/init.d/tuned


clean:
	rm -rf *.pyc monitorplugins/*.pyc tuningplugins/*.pyc $(VERSIONED_NAME) rpm-build-dir

.PHONY: clean archive srpm tag

