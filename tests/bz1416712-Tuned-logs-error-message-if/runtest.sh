#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/tuned/Regression/bz1416712-Tuned-logs-error-message-if
#   Description: Test for BZ#1416712 (Tuned logs error message if)
#   Author: Tereza Cerna <tcerna@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2017 Red Hat, Inc.
#
#   This program is free software: you can redistribute it and/or
#   modify it under the terms of the GNU General Public License as
#   published by the Free Software Foundation, either version 2 of
#   the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied
#   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#   PURPOSE.  See the GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program. If not, see http://www.gnu.org/licenses/.
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="tuned"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlImport "tuned/basic"
        rlServiceStart "tuned"
        tunedProfileBackup
    rlPhaseEnd

    rlPhaseStartTest "Test of profile balanced"
	rlRun "cat /usr/lib/tuned/balanced/tuned.conf | grep alpm="
    	echo > /var/log/tuned/tuned.log
	rlRun "tuned-adm profile balanced"
	rlRun "tuned-adm active | grep balanced"
	rlRun "cat /var/log/tuned/tuned.log | grep -v 'ERROR    tuned.utils.commands: Reading /sys/class/scsi_host/host0/link_power_management_policy'"
	rlRun "cat /var/log/tuned/tuned.log | grep -v 'WARNING  tuned.plugins.plugin_scsi_host: ALPM control file'"
    rlPhaseEnd

    rlPhaseStartTest "Test of profile powersave"
    	rlRun "cat /usr/lib/tuned/powersave/tuned.conf | grep alpm="
	echo > /var/log/tuned/tuned.log
	rlRun "tuned-adm profile powersave"
	rlRun "tuned-adm active | grep powersave"
	rlRun "cat /var/log/tuned/tuned.log | grep -v 'ERROR    tuned.utils.commands: Reading /sys/class/scsi_host/host0/link_power_management_policy'"
	rlRun "cat /var/log/tuned/tuned.log | grep -v 'WARNING  tuned.plugins.plugin_scsi_host: ALPM control file'"
    rlPhaseEnd

    rlPhaseStartCleanup
    	tunedProfileRestore
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
