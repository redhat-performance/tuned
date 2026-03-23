#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/tuned/Sanity/make-rpm
#   Description: sanity check for 'make rpm'
#   Author: Jaroslav Škarvada <jskarvad@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright Red Hat
#
#   SPDX-License-Identifier: GPL-2.0-or-later WITH GPL-CC-1.0
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="tuned"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
        rlRun "rlFetchSrcForInstalled $PACKAGE || yumdownloader --source $PACKAGE"
        rlRun "mkdir -p ./rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}"
        rlFileBackup --clean "~/.rpmmacros"
        rlRun "echo \"%_topdir `pwd`/rpmbuild\" > ~/.rpmmacros"
        rlRun "rpm --nodeps -i *.src.rpm"
        rlRun "VER=`rpm -qp tuned-*.src.rpm --qf \"%{version}\"`"
        rlRun "PYTHON=/usr/bin/python3"
        rlRun "$PYTHON --version || PYTHON=/usr/bin/python"
        rlRun "pushd rpmbuild/SPECS"
        rlRun "dnf builddep -y tuned.spec || yum-builddep -y tuned.spec"
        rlRun "rpmbuild --nodeps -bp tuned.spec"
        rlRun "popd"
        rlRun "cp -a rpmbuild/BUILD/tuned-$VER . || cp -a rpmbuild/BUILD/tuned-$VER-build/tuned-$VER ."
        rlRun "pushd ./tuned-$VER"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "make rpm PYTHON=$PYTHON"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "popd"
        rlFileRestore
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
