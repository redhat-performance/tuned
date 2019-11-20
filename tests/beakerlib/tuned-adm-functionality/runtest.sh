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
#   Copyright (c) 2012 Red Hat, Inc. All rights reserved.
#
#   This copyrighted material is made available to anyone wishing
#   to use, modify, copy, or redistribute it subject to the terms
#   and conditions of the GNU General Public License version 2.
#
#   This program is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied
#   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#   PURPOSE. See the GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public
#   License along with this program; if not, write to the Free
#   Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
#   Boston, MA 02110-1301, USA.
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
        tunedProfileRestore
        rlServiceRestore "tuned"
    rlPhaseEnd

rlJournalPrintText
rlJournalEnd
