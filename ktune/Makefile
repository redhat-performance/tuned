NAME = ktune
VERSION = $(shell awk '/^Version:/ {print $$2}' ktune.spec)
RELEASE = $(shell awk '/^Release:/ {print $$2}' ktune.spec)
VERSIONED_NAME = $(NAME)-$(VERSION)

TAG = v$(VERSION)

distarchive: tag archive

archive:
	git archive --format=tar --prefix="$(NAME)-$(VERSION)/" "$(TAG)" | bzip2 >$(NAME)-$(VERSION).tar.bz2
	@echo "The archive is in $(NAME)-$(VERSION).tar.bz2"

tag:
	git tag -f $(TAG)
	git push --tags

srpm: archive
	rm -rf rpm-build-dir
	mkdir rpm-build-dir
	rpmbuild --define "_sourcedir `pwd`/rpm-build-dir" --define "_srcrpmdir `pwd`/rpm-build-dir" \
		--define "_specdir `pwd`/rpm-build-dir" --nodeps -ts $(VERSIONED_NAME).tar.bz2

build: 
	# Nothing to build

changelog:
	git-log > ChangeLog

.PHONY: archive tag srpm

