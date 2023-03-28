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
#   Copyright (c) 2023 Red Hat, Inc.
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
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"

        rlServiceStart "tuned"
        rlImport "tuned/basic"
        tunedProfileBackup
	rlFileBackup "/etc/tuned/active_profile"
        rlFileBackup "/etc/tuned/profile_mode"

        rlRun "mkdir /etc/tuned/test-profile"
        rlServiceStart "tuned"
        sleep 1
	rlFileBackup "/var/log/tuned/tuned.log"
	rlRun "rm -rf /var/log/tuned/tuned.log"
    rlPhaseEnd

    rlPhaseStartTest
	rlRun "pushd /etc/tuned/test-profile"
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
	rlRun "rm -rf /etc/tuned/test-profile"
    rlPhaseEnd

rlJournalPrintText
rlJournalEnd
