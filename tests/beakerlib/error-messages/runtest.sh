#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/tuned/Regression/bz1416712-Tuned-logs-error-message-if
#   Description: Test for BZ#1416712 (TuneD logs error message if)
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
PROFILE_DIR="/usr/lib/tuned/profiles"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlImport "tuned/basic"
        tunedDisableSystemdRateLimitingStart
        rlServiceStart "tuned"
        tunedProfileBackup
    rlPhaseEnd

    rlPhaseStartTest "Test of profile balanced"
        rlRun "cat $PROFILE_DIR/balanced/tuned.conf | grep alpm="
        echo > /var/log/tuned/tuned.log
        rlRun "tuned-adm profile balanced"
        rlRun "tuned-adm active | grep balanced"
        rlRun "cat /var/log/tuned/tuned.log | grep -v 'ERROR    tuned.utils.commands: Reading /sys/class/scsi_host/host0/link_power_management_policy'"
        rlRun "cat /var/log/tuned/tuned.log | grep -v 'WARNING  tuned.plugins.plugin_scsi_host: ALPM control file'"
    rlPhaseEnd

    rlPhaseStartTest "Test of profile powersave"
        rlRun "cat $PROFILE_DIR/powersave/tuned.conf | grep alpm="
        echo > /var/log/tuned/tuned.log
        rlRun "tuned-adm profile powersave"
        rlRun "tuned-adm active | grep powersave"
        rlRun "cat /var/log/tuned/tuned.log | grep -v 'ERROR    tuned.utils.commands: Reading /sys/class/scsi_host/host0/link_power_management_policy'"
        rlRun "cat /var/log/tuned/tuned.log | grep -v 'WARNING  tuned.plugins.plugin_scsi_host: ALPM control file'"
    rlPhaseEnd

    rlPhaseStartCleanup
        tunedDisableSystemdRateLimitingEnd
        tunedProfileRestore
        rlServiceRestore "tuned"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
