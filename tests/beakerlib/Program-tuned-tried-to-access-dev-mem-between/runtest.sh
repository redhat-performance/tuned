#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/tuned/Regression/Program-tuned-tried-to-access-dev-mem-between
#   Description: Test for BZ#1688371 (Program tuned tried to access /dev/mem between)
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
        rlImport "tuned/basic"

        tunedDisableSystemdRateLimitingStart
        rlServiceStop "tuned"
        # systemd can have some issues with quick restarts sometimes
        sleep 1
        rlServiceStart "tuned"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "dmesg | tee TEST_OUT"
        rlAssertNotGrep "Program tuned tried to access /dev/mem" "TEST_OUT"
    rlPhaseEnd

    rlPhaseStartCleanup
        tunedDisableSystemdRateLimitingEnd
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
        rlServiceRestore "tuned"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
