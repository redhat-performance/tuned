#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/tuned/Regression/bz2071418-TuneD-exits-on-duplicate-config-lines-new
#   Description: Test for BZ#2071418 (TuneD exits on duplicate config lines (new)
#   Author: something else <rhack@redhat.com>
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
PROFILE_DIR=/etc/tuned/profiles

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE


        rlImport "tuned/basic"
        rlServiceStart "tuned"
        tunedProfileBackup

        rlRun "mkdir $PROFILE_DIR/test-profile"
        rlRun "pushd $PROFILE_DIR/test-profile"
        cat << EOF > tuned.conf
[sysctl]
kernel.sem = 1250 256000 100 8192
kernel.sem = 1250 256000 100 8192

[selinux]
avc_cache_threshold=8192 
avc_cache_threshold=16384
EOF

        rlRun "popd"

        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "tuned-adm profile test-profile"
        rlRun "tuned-adm verify"

        rlAssertGrep "test-profile" "/etc/tuned/active_profile"

	# last value from config is used
	rlAssertGrep "16384$"  /sys/fs/selinux/avc/cache_threshold
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"

        tunedProfileRestore
        rlServiceRestore "tuned"

        rlRun "rm -rf $PROFILE_DIR/test-profile"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
