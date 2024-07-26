#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/tuned/Regression/Traceback-caused-by-scheduler-plugin-with
#   Description: Test for BZ#2179362 (Traceback caused by scheduler plugin with)
#   Author: Robin Hack <rhack@redhat.com>
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

        rlServiceStart "tuned"
        rlImport "tuned/basic"
        tunedProfileBackup
        rlFileBackup "/etc/tuned/active_profile"
        rlFileBackup "/etc/tuned/profile_mode"

        PROFILE_DIR=$(tunedGetProfilesBaseDir)

        rlRun "mkdir -p ${PROFILE_DIR}/test-profile"
        rlServiceStop "tuned"
        sleep 1
        rlFileBackup "/var/log/tuned/tuned.log"
        rlRun "rm -rf /var/log/tuned/tuned.log"
        rlServiceStart "tuned"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "pushd $PROFILE_DIR/test-profile"
        cat << EOF > tuned.conf
[scheduler]
runtime=0
EOF
        rlRun "popd"

        rlRun "tuned-adm profile test-profile"
        rlServiceStop "tuned"
        sleep 3
        rlServiceStart "tuned"
        sleep 3
        rlServiceStop "tuned"

        rlAssertNotGrep "Traceback" "/var/log/tuned/tuned.log"
        rlAssertNotGrep "object has no attribute '_evlist'" "/var/log/tuned/tuned.log"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlServiceStart "tuned"
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"

        tunedProfileRestore
        rlServiceStop "tuned"
        rlFileRestore

        rlServiceRestore "tuned"
        rlRun "rm -rf $PROFILE_DIR/test-profile"
    rlPhaseEnd

rlJournalPrintText
rlJournalEnd
