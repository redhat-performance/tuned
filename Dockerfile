ARG base=quay.io/centos-bootc/centos-bootc:stream10

FROM $base as build
COPY tuned.spec /tmp/tuned.spec
# This installs our package dependencies, and we want to cache it independently of the rest.
RUN <<EORUN
set -xeuo pipefail
dnf -y install rpm-build
dnf -y builddep /tmp/tuned.spec
EORUN
# Now copy the rest of the source
COPY . /build
WORKDIR /build
RUN <<EORUN
set -xeuo pipefail
mkdir -p /var/roothome
make rpm
mkdir -p /out
mv ~/rpmbuild/RPMS/noarch/tuned-2*.rpm /out
EORUN

FROM $base
RUN --mount=from=build,target=/build,type=bind <<EORUN
set -xeuo pipefail
dnf -y install /build/out/*.rpm
dnf clean all
rm -rf /var/{lib,cache,log}/*
bootc container lint --fatal-warnings
EORUN

