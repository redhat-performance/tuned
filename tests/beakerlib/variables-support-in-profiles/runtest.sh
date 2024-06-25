#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/tuned/Sanity/variables-support-in-profiles
#   Description: variables support in profiles
#   Author: Branislav Blaskovic <bblaskov@redhat.com>
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
PROFILE_DIR="/usr/lib/tuned/profiles"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlImport "tuned/basic"
        tunedDisableSystemdRateLimitingStart
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
        rlServiceStart "tuned"
        tunedProfileBackup
        rlFileBackup "$PROFILE_DIR/balanced/tuned.conf"

        echo "
[variables]
SWAPPINESS1 = 70
SWAPPINESS2 = \${SWAPPINESS1}

[sysctl]
vm.swappiness = \${SWAPPINESS2}
" >> "$PROFILE_DIR/balanced/tuned.conf"

        rlRun "cat $PROFILE_DIR/balanced/tuned.conf"

        OLD_SWAPPINESS=$(sysctl -n vm.swappiness)

    rlPhaseEnd

    rlPhaseStartTest
        rlRun "tuned-adm profile balanced"
        rlRun -s "sysctl -n vm.swappiness"
        rlAssertGrep "70" "$rlRun_LOG"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "sysctl vm.swappiness=$OLD_SWAPPINESS"
        tunedDisableSystemdRateLimitingEnd
        rlFileRestore
        tunedProfileRestore
        rlServiceRestore "tuned"
        rlRun "systemctl daemon-reload"
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
