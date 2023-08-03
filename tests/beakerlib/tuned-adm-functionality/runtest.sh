#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/tuned/Sanity/tuned-adm-functionality
#   Description: Check functionality of tuned-adm tool.
#   Author: Tereza Cerna <tcerna@redhat.com>
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
LOG_FILE="profile.log"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlImport "tuned/basic"
        tunedProfileBackup
        tunedDisableSystemdRateLimitingStart
    rlPhaseEnd

    rlPhaseStartTest "Test tuned-adm LIST"
        rlServiceStart "tuned"
        rlRun "tuned-adm list" 0
        rlServiceStop "tuned"
        rlRun "tuned-adm list" 0
    rlPhaseEnd

    rlPhaseStartTest "Test tuned-adm ACTIVE"
        rlServiceStart "tuned"
        rlRun "tuned-adm active" 0
        rlServiceStop "tuned"
        rlRun "tuned-adm active" 0
    rlPhaseEnd

    rlPhaseStartTest "Test tuned-adm OFF"
        rlServiceStart "tuned"
        rlRun "tuned-adm off" 0
        rlServiceStop "tuned"
        rlRun "tuned-adm off" 1
    rlPhaseEnd

    rlPhaseStartTest "Test tuned-adm PROFILE"
        rlServiceStart "tuned"
        rlRun "tuned-adm profile virtual-guest" 0
        sleep 5
        rlServiceStop "tuned"
        rlRun "tuned-adm profile virtual-host" 0
        sleep 5
    rlPhaseEnd

    rlPhaseStartTest "Test tuned-adm PROFILE_INFO"
        rlServiceStart "tuned"
        rlRun "tuned-adm profile_info" 0
        rlServiceStop "tuned"
        rlRun "tuned-adm profile_info" 0
    rlPhaseEnd

    rlPhaseStartTest "Test tuned-adm RECOMMEND"
        rlServiceStart "tuned"
        rlRun "tuned-adm recommend" 0
        rlServiceStop "tuned"
        rlRun "tuned-adm recommend" 0
    rlPhaseEnd

    rlPhaseStartTest "Test tuned-adm VERIFY"
        echo > /var/log/tuned/tuned.log
        rlServiceStart "tuned"
        rlRun "tuned-adm verify --ignore-missing" 0 
        rlRun "cat /var/log/tuned/tuned.log | grep ERROR" 1
        rlServiceStop "tuned"
        rlRun "tuned-adm verify --ignore-missing" 1
        rlRun "cat /var/log/tuned/tuned.log | grep ERROR" 1
    rlPhaseEnd

    rlPhaseStartCleanup
        tunedDisableSystemdRateLimitingEnd
        tunedProfileRestore
        rlServiceRestore "tuned"
    rlPhaseEnd

rlJournalPrintText
rlJournalEnd
