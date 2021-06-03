#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/tuned/Regression/Tuned-takes-too-long-to-reload-start-when-ulimit
#   Description: Test for BZ#1663412 (TuneD takes too long to reload/start when "ulimit)
#   Author: Robin Hack <rhack@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2019 Red Hat, Inc.
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
        rlServiceStop "tuned"
        rlFileBackup "/etc/tuned/tuned-main.conf"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "sed 's/daemon = 1/daemon = 0/g' /etc/tuned/tuned-main.conf > /etc/tuned/tuned-main.conf.new"
        rlRun "mv /etc/tuned/tuned-main.conf.new /etc/tuned/tuned-main.conf"
        rlRun "ulimit -H -n 1048576"
        rlRun "ulimit -S -n 1048576"
        rlRun "tuned --debug 2>&1 | tee TEST_OUT"
        rlAssertNotGrep "tuned.plugins.plugin_sysctl: executing \['sysctl'," TEST_OUT
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"

        rlFileRestore
        rlServiceRestore "tuned"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
